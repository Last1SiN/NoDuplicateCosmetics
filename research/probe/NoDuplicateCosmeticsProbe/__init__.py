from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
import re

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook, keybind
from unrealsdk import logging, make_struct
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmeticsProbe supports Borderlands 3 only"

BALANCE_POST_BEGIN_PLAY = "/Script/GbxInventory.InventoryBalanceStateComponent:PostBeginPlay"

WORLD_POOL_PATH = (
    "/Game/GameData/Loot/ItemPools/ItemPool_SkinsAndMisc."
    "ItemPool_SkinsAndMisc"
)

# Probe-only readiness sentinel. Probe 0.4.0 proved this exact customization is owned
# on the test profile once the player/profile state is actually ready. We use it here
# only to prevent the early-startup false-negative observed in that same run.
READINESS_CUSTOMIZATION_PATH = (
    "/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/"
    "CustomHead_Siren_4.CustomHead_Siren_4"
)
READINESS_BALANCE_PATH = (
    "/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/"
    "CustomHead_Siren_4.InvBal_CustomHead_Siren_4"
)

WORLD_BATCH_REQUESTS = 384

_oak_blueprint_library: UObject | None = None
_world_pool: UObject | None = None

_balance_objects: dict[str, UObject] = {}
_customization_by_balance: dict[str, tuple[str, UObject]] = {}
_world_balance_paths: set[str] = set()
_world_leaf_records: list[dict[str, Any]] = []
_pool_direct_leaves: dict[str, list[dict[str, Any]]] = defaultdict(list)

_mutation_records: list[dict[str, Any]] = []
_mutation_applied = False
_plan_generation = 0

_active_batch = "<none>"
_batch_requests = 0
_batch_observed = 0
_batch_owned_hits = 0
_batch_unresolved_hits = 0
_batch_sentinel_hits = 0
_batch_counts: Counter[str] = Counter()
_batch_owned_counts: Counter[str] = Counter()


def _path(obj: Any) -> str:
    if obj is None:
        return "<None>"
    try:
        return str(obj._path_name())
    except Exception:
        return "<unreadable-path>"


def _class_name(obj: Any) -> str:
    if obj is None:
        return "<None>"
    try:
        return str(obj.Class.Name)
    except Exception:
        return type(obj).__name__


def _is_a(obj: Any, class_name: str) -> bool:
    if obj is None:
        return False
    try:
        cls = obj.Class
        while cls is not None:
            if str(cls.Name) == class_name:
                return True
            cls = cls.SuperStruct
    except Exception:
        pass
    return class_name in _class_name(obj)


def _package_from_object_path(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _load_object(class_name: str, path: str, *, log_errors: bool = True) -> UObject | None:
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception as exc:
        if log_errors:
            logging.error(f"[NDCWorldProbe] load_package failed path={path}: {exc}")
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception as exc:
        if log_errors:
            logging.error(f"[NDCWorldProbe] find_object failed class={class_name} path={path}: {exc}")
        return None


def _candidate_path(value: Any) -> str:
    if value is None:
        return "<None>"
    p = _path(value)
    if p != "<unreadable-path>":
        return p
    try:
        text = str(value)
    except Exception:
        return "<unreadable>"
    match = re.search(r"(/Game/[^\'\"\s>)]+)", text)
    return match.group(1) if match else text


def _entry_balance_path(entry: Any) -> str:
    for name in ("ResolvedInventoryBalanceData", "InventoryBalanceData"):
        try:
            candidate = getattr(entry, name)
        except Exception:
            continue
        path = _candidate_path(candidate)
        if path not in ("<None>", "<unreadable>", "<unreadable-path>"):
            return path
    return "<unresolved>"


def _entry_child_pool(entry: Any) -> UObject | None:
    try:
        child = entry.ItemPoolData
    except Exception:
        return None
    return child


def _load_balance(path: str) -> UObject | None:
    if path in _balance_objects:
        return _balance_objects[path]
    obj = _load_object("CustomizationInventoryBalanceData", path, log_errors=False)
    if obj is None:
        obj = _load_object("InventoryBalanceData", path, log_errors=False)
    if obj is not None:
        _balance_objects[path] = obj
    return obj


def _weight_signature(weight: Any) -> tuple[Any, ...]:
    try:
        dt = weight.DataTableValue
        data_table = _path(dt.DataTable)
        row_name = str(dt.RowName)
        value_name = str(dt.ValueName)
    except Exception:
        data_table = "<unreadable>"
        row_name = "<unreadable>"
        value_name = "<unreadable>"
    return (
        float(weight.BaseValueConstant),
        data_table,
        row_name,
        value_name,
        _path(weight.BaseValueAttribute),
        _path(weight.AttributeInitializer),
        float(weight.BaseValueScale),
    )


def _weight_text(sig: tuple[Any, ...]) -> str:
    return (
        "BaseValueConstant={!r}, DataTable={!r}, RowName={!r}, ValueName={!r}, "
        "BaseValueAttribute={!r}, AttributeInitializer={!r}, BaseValueScale={!r}"
    ).format(*sig)


def _simple_positive_constant(sig: tuple[Any, ...]) -> bool:
    constant, data_table, _row, _value, base_attr, initializer, _scale = sig
    return (
        float(constant) > 0.0
        and data_table == "<None>"
        and base_attr == "<None>"
        and initializer == "<None>"
    )


def _profile_ready() -> bool:
    try:
        pc = get_pc()
        if pc is None or pc.Pawn is None:
            logging.info("[NDCWorldProbe] PROFILE_NOT_READY no local player pawn yet")
            return False
    except Exception as exc:
        logging.info(f"[NDCWorldProbe] PROFILE_NOT_READY get_pc/pawn failed: {exc}")
        return False

    sentinel = _load_object("OakCustomizationData", READINESS_CUSTOMIZATION_PATH, log_errors=False)
    if sentinel is None:
        logging.error("[NDCWorldProbe] PROFILE_NOT_READY readiness sentinel asset unavailable")
        return False
    try:
        owned = bool(pc.IsCustomizationUnlocked(sentinel))
    except Exception as exc:
        logging.info(f"[NDCWorldProbe] PROFILE_NOT_READY readiness query failed: {exc}")
        return False
    if not owned:
        logging.info(
            "[NDCWorldProbe] PROFILE_NOT_READY readiness sentinel Motosaurus currently reports owned=NO; "
            "retry after normal game/profile load"
        )
        return False
    return True


def _collect_world_graph() -> bool:
    global _world_pool

    _balance_objects.clear()
    _customization_by_balance.clear()
    _world_balance_paths.clear()
    _world_leaf_records.clear()
    _pool_direct_leaves.clear()

    root = _load_object("ItemPoolData", WORLD_POOL_PATH)
    if root is None:
        return False
    _world_pool = root

    visited: set[str] = set()
    unresolved = 0

    def walk(pool: UObject, depth: int) -> None:
        nonlocal unresolved
        pool_path = _path(pool)
        if pool_path in visited:
            return
        visited.add(pool_path)

        try:
            entries = list(pool.BalancedItems)
        except Exception as exc:
            logging.error(f"[NDCWorldProbe] GRAPH pool unreadable path={pool_path}: {exc}")
            unresolved += 1
            return

        logging.info(
            f"[NDCWorldProbe] GRAPH_POOL depth={depth} path={pool_path} entries={len(entries)}"
        )

        for idx in range(len(entries)):
            live = pool.BalancedItems[idx]
            child = _entry_child_pool(live)
            if child is not None:
                logging.info(
                    f"[NDCWorldProbe] GRAPH_EDGE depth={depth} parent={pool_path} idx={idx} child={_path(child)}"
                )
                walk(child, depth + 1)
                continue

            balance_path = _entry_balance_path(live)
            if not balance_path.startswith("/Game/"):
                logging.error(
                    f"[NDCWorldProbe] GRAPH_UNRESOLVED parent={pool_path} idx={idx} balance={balance_path}"
                )
                unresolved += 1
                continue

            balance = _load_balance(balance_path)
            if balance is None:
                logging.error(
                    f"[NDCWorldProbe] GRAPH_UNRESOLVED could not load balance parent={pool_path} "
                    f"idx={idx} balance={balance_path}"
                )
                unresolved += 1
                continue

            record = {
                "pool": pool,
                "pool_path": pool_path,
                "index": idx,
                "balance": balance,
                "balance_path": balance_path,
            }
            _world_leaf_records.append(record)
            _pool_direct_leaves[pool_path].append(record)
            _world_balance_paths.add(balance_path)

    walk(root, 0)

    if unresolved:
        logging.error(f"[NDCWorldProbe] GRAPH_FAIL unresolved={unresolved}; refusing mutation plan")
        return False

    logging.info(
        f"[NDCWorldProbe] GRAPH_READY pools={len(visited)} leaves={len(_world_leaf_records)}"
    )
    return True


def _rebuild_customization_map() -> None:
    _customization_by_balance.clear()
    for kind in (
        "OakCustomizationData",
        "OakInventoryCustomizationPartData",
        "CrewQuartersDecorationItemData",
    ):
        try:
            candidates = list(unrealsdk.find_all(kind, exact=False))
        except Exception as exc:
            logging.error(f"[NDCWorldProbe] find_all failed kind={kind}: {exc}")
            continue
        for candidate in candidates:
            try:
                balance = candidate.BalanceData
            except Exception:
                continue
            path = _path(balance)
            if path.startswith("/Game/"):
                _customization_by_balance[path] = (kind, candidate)


def _owned_from_mapping(balance_path: str) -> tuple[bool | None, str]:
    mapped = _customization_by_balance.get(balance_path)
    if mapped is None:
        return None, "<unmapped>"
    kind, data = mapped
    try:
        pc = get_pc()
        if kind == "OakCustomizationData":
            return bool(pc.IsCustomizationUnlocked(data)), kind
        if kind == "OakInventoryCustomizationPartData":
            return bool(pc.IsInventoryCustomizationPartUnlocked(data)), kind
        if kind == "CrewQuartersDecorationItemData":
            return bool(pc.IsCrewQuartersDecorationUnlocked(data)), kind
    except Exception as exc:
        logging.error(
            f"[NDCWorldProbe] ownership query failed kind={kind} balance={balance_path}: {exc}"
        )
        return None, kind
    return None, kind


def _prepare_plan() -> bool:
    global _plan_generation, _mutation_records

    if _mutation_applied:
        logging.error("[NDCWorldProbe] PLAN refused while mutation is active")
        return False
    if not _profile_ready():
        return False
    if not _collect_world_graph():
        return False

    _rebuild_customization_map()
    _mutation_records = []
    unresolved = 0
    owned_total = 0
    already_zero_owned = 0
    pool_owned: Counter[str] = Counter()
    pool_total: Counter[str] = Counter()

    for record in _world_leaf_records:
        path = record["balance_path"]
        balance = record["balance"]
        if not _is_a(balance, "CustomizationInventoryBalanceData"):
            logging.error(
                f"[NDCWorldProbe] PLAN_UNEXPECTED_NONCOSMETIC pool={record['pool_path']} "
                f"idx={record['index']} balance={path} class={_class_name(balance)}"
            )
            unresolved += 1
            continue

        pool_total[record["pool_path"]] += 1
        owned, kind = _owned_from_mapping(path)
        if owned is None:
            logging.error(
                f"[NDCWorldProbe] PLAN_UNRESOLVED_OWNERSHIP pool={record['pool_path']} "
                f"idx={record['index']} balance={path} kind={kind}"
            )
            unresolved += 1
            continue
        if not owned:
            continue

        owned_total += 1
        pool_owned[record["pool_path"]] += 1
        live_entry = record["pool"].BalancedItems[record["index"]]
        sig = _weight_signature(live_entry.Weight)
        if float(sig[0]) == 0.0 and sig[1] == "<None>" and sig[4] == "<None>" and sig[5] == "<None>":
            already_zero_owned += 1
            logging.info(
                f"[NDCWorldProbe] PLAN_OWNED_ALREADY_ZERO pool={record['pool_path']} "
                f"idx={record['index']} balance={path}"
            )
            continue
        if not _simple_positive_constant(sig):
            logging.error(
                f"[NDCWorldProbe] PLAN_UNSUPPORTED_OWNED_WEIGHT pool={record['pool_path']} "
                f"idx={record['index']} balance={path} weight=({_weight_text(sig)})"
            )
            unresolved += 1
            continue

        _mutation_records.append(
            {
                **record,
                "kind": kind,
                "original_signature": sig,
                "original_constant": float(sig[0]),
            }
        )

    exhausted: list[str] = []
    for pool_path, total in pool_total.items():
        if total > 0 and pool_owned[pool_path] >= total:
            exhausted.append(pool_path)

    for pool_path in sorted(pool_total):
        logging.info(
            f"[NDCWorldProbe] PLAN_POOL path={pool_path} direct_cosmetic_leaves={pool_total[pool_path]} "
            f"owned={pool_owned[pool_path]}"
        )

    if exhausted:
        for pool_path in exhausted:
            logging.error(
                f"[NDCWorldProbe] PLAN_EXHAUSTED_POOL_BLOCKER path={pool_path}; "
                "parent exhaustion behavior is intentionally not mutated in this front"
            )
        unresolved += len(exhausted)

    if unresolved:
        logging.error(
            f"[NDCWorldProbe] PLAN_FAIL blockers={unresolved} owned_total={owned_total} "
            f"mutation_candidates={len(_mutation_records)} already_zero_owned={already_zero_owned}"
        )
        _mutation_records = []
        return False

    _plan_generation += 1
    logging.info(
        f"[NDCWorldProbe] PLAN_READY generation={_plan_generation} pools_with_leaves={len(pool_total)} "
        f"leaves={sum(pool_total.values())} owned_total={owned_total} "
        f"mutation_candidates={len(_mutation_records)} already_zero_owned={already_zero_owned}"
    )
    for rec in _mutation_records:
        logging.info(
            f"[NDCWorldProbe] PLAN_MUTATE pool={rec['pool_path']} idx={rec['index']} "
            f"balance={rec['balance_path']} kind={rec['kind']} "
            f"weight=({_weight_text(rec['original_signature'])})"
        )
    return True


def _rollback_applied(applied: list[dict[str, Any]], reason: str) -> bool:
    ok = True
    logging.error(f"[NDCWorldProbe] ROLLBACK_BEGIN reason={reason} entries={len(applied)}")
    for rec in reversed(applied):
        pool = rec["pool"]
        idx = rec["index"]
        expected_owned = (0.0,) + rec["original_signature"][1:]
        current = _weight_signature(pool.BalancedItems[idx].Weight)
        if current != expected_owned:
            logging.error(
                f"[NDCWorldProbe] ROLLBACK_GUARD_FAIL pool={rec['pool_path']} idx={idx} "
                f"balance={rec['balance_path']} current=({_weight_text(current)})"
            )
            ok = False
            continue
        try:
            pool.BalancedItems[idx].Weight.BaseValueConstant = rec["original_constant"]
        except Exception as exc:
            logging.error(
                f"[NDCWorldProbe] ROLLBACK_WRITE_FAIL pool={rec['pool_path']} idx={idx}: {exc}"
            )
            ok = False
            continue
        restored = _weight_signature(pool.BalancedItems[idx].Weight)
        if restored != rec["original_signature"]:
            logging.error(
                f"[NDCWorldProbe] ROLLBACK_VERIFY_FAIL pool={rec['pool_path']} idx={idx}"
            )
            ok = False
    logging.info(f"[NDCWorldProbe] ROLLBACK_END ok={ok}")
    return ok


def _apply_plan() -> None:
    global _mutation_applied

    if _mutation_applied:
        logging.info("[NDCWorldProbe] FILTER already active")
        return
    if not _prepare_plan():
        return
    if not _mutation_records:
        logging.info("[NDCWorldProbe] FILTER no positive-weight owned leaves require mutation")
        return

    applied: list[dict[str, Any]] = []
    for rec in _mutation_records:
        pool = rec["pool"]
        idx = rec["index"]
        current = _weight_signature(pool.BalancedItems[idx].Weight)
        if current != rec["original_signature"]:
            _rollback_applied(applied, "pre-write signature changed")
            logging.error(
                f"[NDCWorldProbe] FILTER_FAIL signature changed pool={rec['pool_path']} idx={idx}"
            )
            return
        try:
            pool.BalancedItems[idx].Weight.BaseValueConstant = 0.0
        except Exception as exc:
            _rollback_applied(applied, "write exception")
            logging.error(
                f"[NDCWorldProbe] FILTER_FAIL write pool={rec['pool_path']} idx={idx}: {exc}"
            )
            return
        after = _weight_signature(pool.BalancedItems[idx].Weight)
        expected = (0.0,) + rec["original_signature"][1:]
        if after != expected:
            if float(after[0]) == 0.0:
                applied.append(rec)
            _rollback_applied(applied, "post-write verification")
            logging.error(
                f"[NDCWorldProbe] FILTER_FAIL verify pool={rec['pool_path']} idx={idx} "
                f"after=({_weight_text(after)})"
            )
            return
        applied.append(rec)

    _mutation_applied = True
    logging.info(
        f"[NDCWorldProbe] FILTER_APPLY PASS entries={len(applied)} generation={_plan_generation}"
    )


def _restore_plan() -> None:
    global _mutation_applied

    if not _mutation_applied:
        logging.info("[NDCWorldProbe] RESTORE no active mutation")
        return

    ok = True
    restored_count = 0
    for rec in reversed(_mutation_records):
        pool = rec["pool"]
        idx = rec["index"]
        current = _weight_signature(pool.BalancedItems[idx].Weight)
        expected_owned = (0.0,) + rec["original_signature"][1:]
        if current != expected_owned:
            logging.error(
                f"[NDCWorldProbe] RESTORE_GUARD_FAIL pool={rec['pool_path']} idx={idx} "
                f"balance={rec['balance_path']} current=({_weight_text(current)})"
            )
            ok = False
            continue
        try:
            pool.BalancedItems[idx].Weight.BaseValueConstant = rec["original_constant"]
        except Exception as exc:
            logging.error(
                f"[NDCWorldProbe] RESTORE_WRITE_FAIL pool={rec['pool_path']} idx={idx}: {exc}"
            )
            ok = False
            continue
        restored = _weight_signature(pool.BalancedItems[idx].Weight)
        if restored != rec["original_signature"]:
            logging.error(
                f"[NDCWorldProbe] RESTORE_VERIFY_FAIL pool={rec['pool_path']} idx={idx}"
            )
            ok = False
            continue
        restored_count += 1

    if ok and restored_count == len(_mutation_records):
        _mutation_applied = False
        logging.info(
            f"[NDCWorldProbe] RESTORE PASS exact signatures restored entries={restored_count}"
        )
    else:
        logging.error(
            f"[NDCWorldProbe] RESTORE INCOMPLETE restored={restored_count}/{len(_mutation_records)}"
        )


def _verify_mutation_state(label: str) -> None:
    if not _mutation_records:
        logging.info(f"[NDCWorldProbe] VERIFY label={label} no captured mutation records")
        return
    good = 0
    bad = 0
    for rec in _mutation_records:
        current = _weight_signature(rec["pool"].BalancedItems[rec["index"]].Weight)
        expected = (
            (0.0,) + rec["original_signature"][1:]
            if _mutation_applied
            else rec["original_signature"]
        )
        if current == expected:
            good += 1
        else:
            bad += 1
            logging.error(
                f"[NDCWorldProbe] VERIFY_MISMATCH label={label} pool={rec['pool_path']} "
                f"idx={rec['index']} balance={rec['balance_path']} "
                f"expected=({_weight_text(expected)}) current=({_weight_text(current)})"
            )
    logging.info(
        f"[NDCWorldProbe] VERIFY label={label} mutation_applied={_mutation_applied} good={good} bad={bad}"
    )


def _reset_batch(label: str, requests: int) -> None:
    global _active_batch, _batch_requests, _batch_observed, _batch_owned_hits
    global _batch_unresolved_hits, _batch_sentinel_hits, _batch_counts, _batch_owned_counts
    _active_batch = label
    _batch_requests = requests
    _batch_observed = 0
    _batch_owned_hits = 0
    _batch_unresolved_hits = 0
    _batch_sentinel_hits = 0
    _batch_counts = Counter()
    _batch_owned_counts = Counter()


def _spawn_world(label: str, count: int = WORLD_BATCH_REQUESTS) -> None:
    global _oak_blueprint_library, _world_pool

    if not _profile_ready():
        return
    if _world_pool is None or not _world_balance_paths:
        if not _collect_world_graph():
            return
        _rebuild_customization_map()

    try:
        pc = get_pc()
        pawn = pc.Pawn
    except Exception as exc:
        logging.error(f"[NDCWorldProbe] no local pawn: {exc}")
        return
    if pawn is None:
        logging.error("[NDCWorldProbe] no local pawn")
        return

    if _oak_blueprint_library is None:
        try:
            _oak_blueprint_library = unrealsdk.find_class("OakBlueprintLibrary").ClassDefaultObject
        except Exception as exc:
            logging.error(f"[NDCWorldProbe] OakBlueprintLibrary unavailable: {exc}")
            return

    try:
        request = make_struct("SpawnDroppedPickupLootRequest", ContextActor=pawn, ItemPools=_world_pool)
    except Exception as exc:
        logging.error(f"[NDCWorldProbe] could not build spawn request: {exc}")
        return

    _reset_batch(label, count)
    logging.info(
        f"[NDCWorldProbe] BATCH_START label={label} requests={count} "
        f"mutation_applied={_mutation_applied} graph_leaves={len(_world_balance_paths)}"
    )
    for _ in range(count):
        try:
            _oak_blueprint_library.SpawnLootAsync(pawn, request)
        except Exception as exc:
            logging.error(f"[NDCWorldProbe] SpawnLootAsync failed: {exc}")
            break


def _batch_summary(label: str) -> None:
    ratio = (_batch_observed / _batch_requests) if _batch_requests else 0.0
    logging.info(
        f"[NDCWorldProbe] BATCH_SUMMARY request={label} active_batch={_active_batch} "
        f"requests={_batch_requests} observed={_batch_observed} observed_ratio={ratio:.4f} "
        f"owned_hits={_batch_owned_hits} unresolved_hits={_batch_unresolved_hits} "
        f"sentinel_hits={_batch_sentinel_hits} distinct={len(_batch_counts)} "
        f"mutation_applied={_mutation_applied} top={_batch_counts.most_common(15)} "
        f"owned_top={_batch_owned_counts.most_common(15)}"
    )


@keybind("Probe050 Build world ownership plan", "NumPadZero", is_rebindable=False)
def _kb_plan() -> None:
    _prepare_plan()


@keybind("Probe050 Spawn world baseline x384", "NumPadOne", is_rebindable=False)
def _kb_baseline() -> None:
    if _mutation_applied:
        logging.error("[NDCWorldProbe] baseline refused while filter is active; restore first")
        return
    _spawn_world("baseline")


@keybind("Probe050 Baseline summary", "NumPadTwo", is_rebindable=False)
def _kb_baseline_summary() -> None:
    _batch_summary("baseline_summary")


@keybind("Probe050 Apply owned world filter", "NumPadThree", is_rebindable=False)
def _kb_apply() -> None:
    _apply_plan()


@keybind("Probe050 Spawn world filtered x384", "NumPadFour", is_rebindable=False)
def _kb_filtered() -> None:
    if not _mutation_applied:
        logging.error("[NDCWorldProbe] filtered spawn refused because filter is not active")
        return
    _spawn_world("filtered")


@keybind("Probe050 Filtered summary", "NumPadFive", is_rebindable=False)
def _kb_filtered_summary() -> None:
    _batch_summary("filtered_summary")


@keybind("Probe050 Restore all owned weights", "NumPadSix", is_rebindable=False)
def _kb_restore() -> None:
    _restore_plan()


@keybind("Probe050 Spawn world restored x384", "NumPadSeven", is_rebindable=False)
def _kb_restored() -> None:
    if _mutation_applied:
        logging.error("[NDCWorldProbe] restored spawn refused while filter is active")
        return
    _spawn_world("restored")


@keybind("Probe050 Restored summary", "NumPadEight", is_rebindable=False)
def _kb_restored_summary() -> None:
    _batch_summary("restored_summary")


@keybind("Probe050 Verify captured weights", "NumPadNine", is_rebindable=False)
def _kb_verify() -> None:
    _verify_mutation_state("manual")


@hook(BALANCE_POST_BEGIN_PLAY, Type.POST)
def _balance_post_begin_play(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _batch_observed, _batch_owned_hits, _batch_unresolved_hits, _batch_sentinel_hits

    if _active_batch == "<none>" or not _world_balance_paths:
        return
    try:
        balance = obj.GetInventoryBalanceData()
    except Exception:
        return
    path = _path(balance)
    if path not in _world_balance_paths:
        return

    try:
        name = str(obj.GetDisplayName())
    except Exception:
        name = path

    _batch_observed += 1
    _batch_counts[name] += 1
    if path == READINESS_BALANCE_PATH:
        _batch_sentinel_hits += 1

    owned, kind = _owned_from_mapping(path)
    if owned is None:
        _batch_unresolved_hits += 1
        logging.error(
            f"[NDCWorldProbe] BATCH_UNRESOLVED batch={_active_batch} name={name!r} "
            f"balance={path} kind={kind}"
        )
        return
    if owned:
        _batch_owned_hits += 1
        _batch_owned_counts[name] += 1
        logging.info(
            f"[NDCWorldProbe] OWNED_HIT batch={_active_batch} name={name!r} balance={path} kind={kind}"
        )


def on_enable() -> None:
    logging.info(
        "[NDCWorldProbe] ENABLED build=0.5.0 lazy-profile-scan "
        "Num0=plan Num1=baseline384 Num2=baseline_summary Num3=apply "
        "Num4=filtered384 Num5=filtered_summary Num6=restore "
        "Num7=restored384 Num8=restored_summary Num9=verify"
    )


def on_disable() -> None:
    if _mutation_applied:
        logging.info("[NDCWorldProbe] disabling with active mutation; guarded restore first")
        _restore_plan()
    logging.info("[NDCWorldProbe] DISABLED build=0.5.0")


logging.info(
    "[NDCWorldProbe] LOADED build=0.5.0 scope=stock-world-cosmetic-root "
    "mutation=owned-simple-constant-leaves-only parent-exhaustion=fail-closed"
)

mod = build_mod(on_enable=on_enable, on_disable=on_disable)
