from __future__ import annotations

from collections import Counter
import re
from typing import Any

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook, keybind
from unrealsdk import logging, make_struct
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmeticsProbe supports Borderlands 3 only"

BALANCE_POST_BEGIN_PLAY = "/Script/GbxInventory.InventoryBalanceStateComponent:PostBeginPlay"

TARGET_POOL_PATH = (
    "/Game/Pickups/Customizations/_Design/ItemPools/Heads/"
    "ItemPool_Customizations_Heads_Loot_Siren.ItemPool_Customizations_Heads_Loot_Siren"
)
TARGET_BALANCE_PATH = (
    "/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/"
    "CustomHead_Siren_4.InvBal_CustomHead_Siren_4"
)
TARGET_CUSTOMIZATION_PATH = (
    "/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/"
    "CustomHead_Siren_4.CustomHead_Siren_4"
)
TARGET_DISPLAY_NAME = "Motosaurus"
BATCH_REQUESTS = 96

_oak_blueprint_library: UObject | None = None
_target_pool: UObject | None = None
_target_entry_index: int | None = None
_original_weight_signature: tuple[Any, ...] | None = None
_original_constant: float | None = None
_mutation_applied = False

_active_batch = "<none>"
_batch_requests = 0
_batch_observed = 0
_batch_target_hits = 0
_batch_counts: Counter[str] = Counter()
_target_balance_paths: set[str] = set()


def _path(obj: Any) -> str:
    if obj is None:
        return "<None>"
    try:
        return str(obj._path_name())
    except Exception:
        return "<unreadable-path>"


def _package_from_object_path(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _load_object(class_name: str, path: str) -> UObject | None:
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] load_package failed path={path}: {exc}")
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] find_object failed class={class_name} path={path}: {exc}")
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


def _weight_text(signature: tuple[Any, ...]) -> str:
    return (
        "BaseValueConstant={!r}, DataTable={!r}, RowName={!r}, ValueName={!r}, "
        "BaseValueAttribute={!r}, AttributeInitializer={!r}, BaseValueScale={!r}"
    ).format(*signature)


def _weight_is_simple_constant(signature: tuple[Any, ...]) -> bool:
    constant, data_table, _row, _value, base_attr, initializer, _scale = signature
    return (
        float(constant) > 0.0
        and data_table == "<None>"
        and base_attr == "<None>"
        and initializer == "<None>"
    )


def _read_target_entry() -> tuple[Any, Any] | None:
    global _target_pool, _target_entry_index, _original_weight_signature, _original_constant

    pool = _load_object("ItemPoolData", TARGET_POOL_PATH)
    if pool is None:
        return None
    _target_pool = pool

    target_balance = _load_object("InventoryBalanceData", TARGET_BALANCE_PATH)
    if target_balance is None:
        target_balance = _load_object("CustomizationInventoryBalanceData", TARGET_BALANCE_PATH)
    target_custom = _load_object("OakCustomizationData", TARGET_CUSTOMIZATION_PATH)
    if target_custom is None:
        return None

    try:
        owned = bool(get_pc().IsCustomizationUnlocked(target_custom))
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] ownership query failed: {exc}")
        return None

    if not owned:
        logging.error(
            f"[NDCMutationProbe] FAIL-CLOSED: target {TARGET_DISPLAY_NAME!r} is not owned on this profile"
        )
        return None

    try:
        entries = list(pool.BalancedItems)
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] target pool BalancedItems unreadable: {exc}")
        return None

    _target_balance_paths.clear()
    found_idx: int | None = None
    for idx, entry in enumerate(entries):
        path = _entry_balance_path(entry)
        if path.startswith("/Game/"):
            _target_balance_paths.add(path)
        if target_balance is not None:
            try:
                if entry.ResolvedInventoryBalanceData is target_balance:
                    found_idx = idx
            except Exception:
                pass
            if found_idx is None:
                try:
                    if entry.InventoryBalanceData is target_balance:
                        found_idx = idx
                except Exception:
                    pass
        if TARGET_BALANCE_PATH in path:
            found_idx = idx

    if found_idx is None:
        logging.error(
            "[NDCMutationProbe] FAIL-CLOSED: exact Motosaurus balance was not found in the stock Siren head pool"
        )
        for idx, entry in enumerate(entries):
            logging.info(
                f"[NDCMutationProbe] TARGET_POOL_ENTRY idx={idx} balance={_entry_balance_path(entry)}"
            )
        return None

    _target_entry_index = found_idx
    live_entry = pool.BalancedItems[found_idx]
    signature = _weight_signature(live_entry.Weight)

    if _original_weight_signature is None:
        _original_weight_signature = signature
        _original_constant = float(live_entry.Weight.BaseValueConstant)

    logging.info(
        f"[NDCMutationProbe] TARGET_READY pool={TARGET_POOL_PATH} idx={found_idx} "
        f"balance={TARGET_BALANCE_PATH} owned=YES weight=({_weight_text(signature)}) "
        f"entry_count={len(entries)}"
    )

    if not _weight_is_simple_constant(signature) and not _mutation_applied:
        logging.error(
            "[NDCMutationProbe] FAIL-CLOSED: target weight is not the expected simple constant form; no mutation performed"
        )
        return None

    return pool, live_entry


def _verify_current_weight(label: str) -> bool:
    if _target_pool is None or _target_entry_index is None:
        if _read_target_entry() is None:
            return False
    assert _target_pool is not None
    assert _target_entry_index is not None
    sig = _weight_signature(_target_pool.BalancedItems[_target_entry_index].Weight)
    logging.info(f"[NDCMutationProbe] WEIGHT {label} ({_weight_text(sig)})")
    return True


def _apply_filter() -> None:
    global _mutation_applied

    if _mutation_applied:
        logging.info("[NDCMutationProbe] FILTER already applied")
        _verify_current_weight("already_applied")
        return

    prepared = _read_target_entry()
    if prepared is None:
        return
    pool, _entry = prepared
    assert _target_entry_index is not None
    assert _original_weight_signature is not None

    current = _weight_signature(pool.BalancedItems[_target_entry_index].Weight)
    if current != _original_weight_signature:
        logging.error(
            "[NDCMutationProbe] FAIL-CLOSED: target weight changed since baseline capture; refusing to overwrite it"
        )
        logging.error(f"[NDCMutationProbe] expected=({_weight_text(_original_weight_signature)})")
        logging.error(f"[NDCMutationProbe] current=({_weight_text(current)})")
        return

    try:
        pool.BalancedItems[_target_entry_index].Weight.BaseValueConstant = 0.0
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] FILTER mutation write failed: {exc}")
        return

    after = _weight_signature(pool.BalancedItems[_target_entry_index].Weight)
    if float(after[0]) != 0.0 or after[1:] != _original_weight_signature[1:]:
        logging.error(
            "[NDCMutationProbe] FILTER verification failed; attempting immediate rollback"
        )
        try:
            pool.BalancedItems[_target_entry_index].Weight.BaseValueConstant = _original_constant
        except Exception as exc:
            logging.error(f"[NDCMutationProbe] rollback write failed: {exc}")
        _verify_current_weight("after_failed_apply")
        return

    _mutation_applied = True
    logging.info(
        f"[NDCMutationProbe] FILTER_APPLY PASS target={TARGET_DISPLAY_NAME} idx={_target_entry_index} "
        f"before_constant={_original_constant} after_constant=0.0"
    )


def _restore_filter() -> None:
    global _mutation_applied

    if not _mutation_applied:
        logging.info("[NDCMutationProbe] RESTORE no active mutation")
        return
    if _target_pool is None or _target_entry_index is None or _original_weight_signature is None:
        logging.error("[NDCMutationProbe] RESTORE missing ownership state; refusing blind write")
        return

    current = _weight_signature(_target_pool.BalancedItems[_target_entry_index].Weight)
    expected_owned = (0.0,) + _original_weight_signature[1:]
    if current != expected_owned:
        logging.error(
            "[NDCMutationProbe] RESTORE ownership guard failed: current weight no longer equals probe-owned value; leaving it untouched"
        )
        logging.error(f"[NDCMutationProbe] current=({_weight_text(current)})")
        return

    try:
        _target_pool.BalancedItems[_target_entry_index].Weight.BaseValueConstant = _original_constant
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] RESTORE write failed: {exc}")
        return

    restored = _weight_signature(_target_pool.BalancedItems[_target_entry_index].Weight)
    if restored != _original_weight_signature:
        logging.error("[NDCMutationProbe] RESTORE verification FAILED")
        logging.error(f"[NDCMutationProbe] expected=({_weight_text(_original_weight_signature)})")
        logging.error(f"[NDCMutationProbe] restored=({_weight_text(restored)})")
        return

    _mutation_applied = False
    logging.info("[NDCMutationProbe] RESTORE PASS exact weight signature restored")


def _reset_batch(label: str, requests: int) -> None:
    global _active_batch, _batch_requests, _batch_observed, _batch_target_hits, _batch_counts
    _active_batch = label
    _batch_requests = requests
    _batch_observed = 0
    _batch_target_hits = 0
    _batch_counts = Counter()


def _spawn_target(label: str, count: int = BATCH_REQUESTS) -> None:
    global _oak_blueprint_library

    prepared = _read_target_entry()
    if prepared is None:
        return
    pool, _entry = prepared

    try:
        pc = get_pc()
        pawn = pc.Pawn
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] no local pawn: {exc}")
        return
    if pawn is None:
        logging.error("[NDCMutationProbe] no local pawn")
        return

    if _oak_blueprint_library is None:
        try:
            _oak_blueprint_library = unrealsdk.find_class("OakBlueprintLibrary").ClassDefaultObject
        except Exception as exc:
            logging.error(f"[NDCMutationProbe] OakBlueprintLibrary unavailable: {exc}")
            return

    try:
        request = make_struct("SpawnDroppedPickupLootRequest", ContextActor=pawn, ItemPools=pool)
    except Exception as exc:
        logging.error(f"[NDCMutationProbe] could not build spawn request: {exc}")
        return

    _reset_batch(label, count)
    logging.info(
        f"[NDCMutationProbe] BATCH_START label={label} requests={count} mutation_applied={_mutation_applied}"
    )
    for _ in range(count):
        try:
            _oak_blueprint_library.SpawnLootAsync(pawn, request)
        except Exception as exc:
            logging.error(f"[NDCMutationProbe] SpawnLootAsync failed: {exc}")
            break


def _batch_summary(label: str) -> None:
    top = _batch_counts.most_common(12)
    logging.info(
        f"[NDCMutationProbe] BATCH_SUMMARY request={label} active_batch={_active_batch} "
        f"requests={_batch_requests} observed={_batch_observed} "
        f"target_hits={_batch_target_hits} distinct={len(_batch_counts)} "
        f"mutation_applied={_mutation_applied} top={top}"
    )


@keybind("Probe040 Inspect target", "NumPadZero", is_rebindable=False)
def _kb_inspect() -> None:
    _read_target_entry()
    _verify_current_weight("inspect")


@keybind("Probe040 Spawn baseline x96", "NumPadOne", is_rebindable=False)
def _kb_baseline() -> None:
    if _mutation_applied:
        logging.error("[NDCMutationProbe] baseline spawn refused while filter is active; restore first")
        return
    _spawn_target("baseline")


@keybind("Probe040 Baseline summary", "NumPadTwo", is_rebindable=False)
def _kb_baseline_summary() -> None:
    _batch_summary("baseline_summary")


@keybind("Probe040 Apply target exclusion", "NumPadThree", is_rebindable=False)
def _kb_apply() -> None:
    _apply_filter()


@keybind("Probe040 Spawn filtered x96", "NumPadFour", is_rebindable=False)
def _kb_filtered() -> None:
    if not _mutation_applied:
        logging.error("[NDCMutationProbe] filtered spawn refused because filter is not active")
        return
    _spawn_target("filtered")


@keybind("Probe040 Filtered summary", "NumPadFive", is_rebindable=False)
def _kb_filtered_summary() -> None:
    _batch_summary("filtered_summary")


@keybind("Probe040 Restore target weight", "NumPadSix", is_rebindable=False)
def _kb_restore() -> None:
    _restore_filter()


@keybind("Probe040 Spawn restored x96", "NumPadSeven", is_rebindable=False)
def _kb_restored() -> None:
    if _mutation_applied:
        logging.error("[NDCMutationProbe] restored spawn refused while filter is still active")
        return
    _spawn_target("restored")


@keybind("Probe040 Restored summary", "NumPadEight", is_rebindable=False)
def _kb_restored_summary() -> None:
    _batch_summary("restored_summary")


@keybind("Probe040 Verify current weight", "NumPadNine", is_rebindable=False)
def _kb_verify_weight() -> None:
    _verify_current_weight("manual_verify")


@hook(BALANCE_POST_BEGIN_PLAY, Type.POST)
def _balance_post_begin_play(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _batch_observed, _batch_target_hits

    if _active_batch == "<none>":
        return
    try:
        balance = obj.GetInventoryBalanceData()
    except Exception:
        return
    balance_path = _path(balance)

    if _target_balance_paths and balance_path not in _target_balance_paths:
        return

    try:
        name = str(obj.GetDisplayName())
    except Exception:
        name = balance_path

    _batch_observed += 1
    _batch_counts[name] += 1
    if balance_path == TARGET_BALANCE_PATH:
        _batch_target_hits += 1
        logging.info(
            f"[NDCMutationProbe] TARGET_HIT batch={_active_batch} name={name!r} balance={balance_path}"
        )


def on_enable() -> None:
    logging.info(
        "[NDCMutationProbe] ENABLED build=0.4.0 "
        "Num0=inspect Num1=baseline96 Num2=baseline_summary Num3=apply "
        "Num4=filtered96 Num5=filtered_summary Num6=restore "
        "Num7=restored96 Num8=restored_summary Num9=verify_weight"
    )
    _read_target_entry()


def on_disable() -> None:
    if _mutation_applied:
        logging.info("[NDCMutationProbe] disabling with active mutation; restoring first")
        _restore_filter()
    logging.info("[NDCMutationProbe] DISABLED build=0.4.0")


logging.info(
    "[NDCMutationProbe] LOADED build=0.4.0 target=Motosaurus "
    "scope=single-stock-Siren-head-leaf"
)

mod = build_mod(on_enable=on_enable, on_disable=on_disable)
