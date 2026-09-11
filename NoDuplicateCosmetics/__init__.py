from __future__ import annotations

from typing import Any
import re
import time

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook
from unrealsdk import logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmetics supports Borderlands 3 only"

logging.info("[NoDuplicateCosmetics] LOADED candidate=0.1.2")

HUD_FRAME = "/Script/Engine.HUD:ReceiveDrawHUD"
WORLD_POOL_PATH = (
    "/Game/GameData/Loot/ItemPools/ItemPool_SkinsAndMisc."
    "ItemPool_SkinsAndMisc"
)

PLAYER_SETTLE_SECONDS = 2.0
REFRESH_INTERVAL_SECONDS = 1.0

_root_pool: UObject | None = None
_graph_ready = False
_pool_nodes: dict[str, dict[str, Any]] = {}
_leaf_records: dict[tuple[str, int, str], dict[str, Any]] = {}
_customization_by_balance: dict[str, tuple[str, UObject]] = {}

# Entries currently owned by this mod. Each record stores the live pool/index plus
# exact before/after weight signatures so disable/refresh never blindly overwrites a
# later third-party change.
_managed: dict[tuple[str, int, str, str], dict[str, Any]] = {}
_blocked_keys: set[tuple[str, int, str, str]] = set()

_pc_identity: tuple[str, int | None] | None = None
_ready_since: float | None = None
_last_refresh = 0.0
_reported_errors: set[str] = set()
_startup_reported = False


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


def _report_once(token: str, message: str) -> None:
    if token in _reported_errors:
        return
    _reported_errors.add(token)
    logging.error(f"[NoDuplicateCosmetics] {message}")


def _package_from_object_path(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _load_object(class_name: str, path: str, *, log_errors: bool = True) -> UObject | None:
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception as exc:
        if log_errors:
            _report_once(
                f"load-package:{path}",
                f"could not load package for {path}: {type(exc).__name__}: {exc}",
            )
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception as exc:
        if log_errors:
            _report_once(
                f"find-object:{class_name}:{path}",
                f"could not find {class_name} {path}: {type(exc).__name__}: {exc}",
            )
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
            value = getattr(entry, name)
        except Exception:
            continue
        p = _candidate_path(value)
        if p not in ("<None>", "<unreadable>", "<unreadable-path>"):
            return p
    return "<unresolved>"


def _entry_child_pool(entry: Any) -> UObject | None:
    try:
        return entry.ItemPoolData
    except Exception:
        return None


def _load_balance(path: str) -> UObject | None:
    # The world graph should contain customization balances only. Try the specific
    # class first, then the base inventory-balance class for diagnostic safety.
    obj = _load_object("CustomizationInventoryBalanceData", path, log_errors=False)
    if obj is None:
        obj = _load_object("InventoryBalanceData", path, log_errors=False)
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


def _weight_mode(sig: tuple[Any, ...]) -> str:
    constant, data_table, _row, _value, base_attr, initializer, scale = sig

    if data_table != "<None>" or initializer != "<None>":
        return "unsupported"

    if base_attr == "<None>":
        if float(constant) > 0.0:
            return "constant"
        if float(constant) == 0.0:
            return "disabled"
        return "unsupported"

    if base_attr.startswith("/Game/"):
        if float(constant) > 0.0 and float(scale) > 0.0:
            return "attribute"
        if float(constant) == 0.0 and float(scale) == 0.0:
            return "disabled"

    return "unsupported"


def _filtered_signature(original: tuple[Any, ...], mode: str) -> tuple[Any, ...]:
    if mode == "constant":
        return (0.0,) + original[1:]
    if mode == "attribute":
        return (0.0,) + original[1:6] + (0.0,)
    raise ValueError(f"unsupported mutation mode {mode}")


def _entry_key(record: dict[str, Any]) -> tuple[str, int, str, str]:
    target_kind = "edge" if record["child_path"] is not None else "leaf"
    target = record["child_path"] or record["balance_path"]
    return record["pool_path"], record["index"], target_kind, target


def _current_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    return _weight_signature(record["pool"].BalancedItems[record["index"]].Weight)


def _original_for(record: dict[str, Any]) -> tuple[Any, ...]:
    managed = _managed.get(_entry_key(record))
    return managed["original"] if managed is not None else _current_signature(record)


def _collect_graph() -> bool:
    global _root_pool, _graph_ready

    root = _load_object("ItemPoolData", WORLD_POOL_PATH)
    if root is None:
        return False

    pool_nodes: dict[str, dict[str, Any]] = {}
    leaf_records: dict[tuple[str, int, str], dict[str, Any]] = {}
    visiting: set[str] = set()
    complete: set[str] = set()
    blockers: list[str] = []

    def walk(pool: UObject) -> None:
        pool_path = _path(pool)
        if pool_path in complete:
            return
        if pool_path in visiting:
            blockers.append(f"cycle detected at {pool_path}")
            return
        visiting.add(pool_path)

        try:
            count = len(pool.BalancedItems)
        except Exception as exc:
            blockers.append(
                f"cannot read BalancedItems for {pool_path}: {type(exc).__name__}: {exc}"
            )
            visiting.remove(pool_path)
            return

        records: list[dict[str, Any]] = []
        for idx in range(count):
            live = pool.BalancedItems[idx]
            child = _entry_child_pool(live)
            if child is not None:
                child_path = _path(child)
                if not child_path.startswith("/Game/"):
                    blockers.append(
                        f"unresolved child pool at {pool_path}[{idx}]: {child_path}"
                    )
                    continue
                record = {
                    "pool": pool,
                    "pool_path": pool_path,
                    "index": idx,
                    "child": child,
                    "child_path": child_path,
                    "balance": None,
                    "balance_path": None,
                }
                records.append(record)
                walk(child)
                continue

            balance_path = _entry_balance_path(live)
            if not balance_path.startswith("/Game/"):
                blockers.append(
                    f"unresolved balance at {pool_path}[{idx}]: {balance_path}"
                )
                continue
            balance = _load_balance(balance_path)
            if balance is None or not _is_a(balance, "CustomizationInventoryBalanceData"):
                blockers.append(
                    f"non-cosmetic/unresolved balance at {pool_path}[{idx}]: "
                    f"{balance_path} ({_class_name(balance)})"
                )
                continue
            record = {
                "pool": pool,
                "pool_path": pool_path,
                "index": idx,
                "child": None,
                "child_path": None,
                "balance": balance,
                "balance_path": balance_path,
            }
            records.append(record)
            leaf_records[(pool_path, idx, balance_path)] = record

        pool_nodes[pool_path] = {"pool": pool, "entries": records}
        visiting.remove(pool_path)
        complete.add(pool_path)

    walk(root)

    if blockers:
        _report_once("graph:" + blockers[0], f"world graph rejected: {blockers[0]}")
        return False

    if WORLD_POOL_PATH not in pool_nodes or not leaf_records:
        _report_once("graph-empty", "world cosmetic graph resolved without cosmetic leaves")
        return False

    _root_pool = root
    _pool_nodes.clear()
    _pool_nodes.update(pool_nodes)
    _leaf_records.clear()
    _leaf_records.update(leaf_records)
    _graph_ready = True
    return True


def _rebuild_customization_map() -> bool:
    wanted = {record["balance_path"] for record in _leaf_records.values()}
    mapping: dict[str, tuple[str, UObject]] = {}

    for kind in (
        "OakCustomizationData",
        "OakInventoryCustomizationPartData",
        "CrewQuartersDecorationItemData",
    ):
        try:
            candidates = unrealsdk.find_all(kind, exact=False)
        except Exception as exc:
            _report_once(
                f"find-all:{kind}",
                f"could not enumerate {kind}: {type(exc).__name__}: {exc}",
            )
            return False
        for candidate in candidates:
            try:
                balance_path = _path(candidate.BalanceData)
            except Exception:
                continue
            if balance_path in wanted:
                mapping[balance_path] = (kind, candidate)

    missing = wanted.difference(mapping)
    if missing:
        sample = sorted(missing)[0]
        _report_once(
            f"mapping:{sample}",
            f"ownership mapping incomplete; first missing world cosmetic balance: {sample}",
        )
        return False

    _customization_by_balance.clear()
    _customization_by_balance.update(mapping)
    return True


def _owned(balance_path: str) -> bool | None:
    mapped = _customization_by_balance.get(balance_path)
    if mapped is None:
        return None
    kind, data = mapped
    try:
        pc = get_pc()
        if pc is None:
            return None
        if kind == "OakCustomizationData":
            return bool(pc.IsCustomizationUnlocked(data))
        if kind == "OakInventoryCustomizationPartData":
            return bool(pc.IsInventoryCustomizationPartUnlocked(data))
        if kind == "CrewQuartersDecorationItemData":
            return bool(pc.IsCrewQuartersDecorationUnlocked(data))
    except Exception as exc:
        _report_once(
            f"ownership:{kind}:{balance_path}",
            f"ownership query failed for {balance_path}: {type(exc).__name__}: {exc}",
        )
        return None
    return None


def _restore_record(key: tuple[str, int, str, str], record: dict[str, Any]) -> bool:
    current = _current_signature(record)
    original = record["original"]
    filtered = record["filtered"]

    if current == original:
        _managed.pop(key, None)
        return True

    if current != filtered:
        _blocked_keys.add(key)
        _managed.pop(key, None)
        _report_once(
            f"restore-conflict:{key}",
            f"weight changed after filtering; leaving external value untouched at {key}",
        )
        return False

    live = record["pool"].BalancedItems[record["index"]].Weight
    try:
        live.BaseValueConstant = float(original[0])
        if record["mode"] == "attribute":
            live.BaseValueScale = float(original[6])
    except Exception as exc:
        _report_once(
            f"restore-write:{key}",
            f"failed to restore {key}: {type(exc).__name__}: {exc}",
        )
        return False

    if _current_signature(record) != original:
        _report_once(
            f"restore-verify:{key}",
            f"restored weight did not match captured signature at {key}",
         )
        return False

    _managed.pop(key, None)
    return True


def _restore_all() -> None:
    # Snapshot because _restore_record removes successful/conflicted records.
    for key, record in list(_managed.items()):
        _restore_record(key, record)


def _apply_record(record: dict[str, Any], mode: str) -> bool:
    key = _entry_key(record)
    if key in _blocked_keys:
        return False

    existing = _managed.get(key)
    if existing is not None:
        # Refresh object reference in case the graph was rebuilt around the same entry.
        existing["pool"] = record["pool"]
        existing["index"] = record["index"]
        current = _current_signature(existing)
        if current == existing["filtered"]:
            return True
        if current != existing["original"]:
            _blocked_keys.add(key)
            _managed.pop(key, None)
            _report_once(
                f"managed-conflict:{key}",
                f"managed weight changed externally; filtering disabled for {key}",
            )
            return False
        original = existing["original"]
        mode = existing["mode"]
    else:
        original = _current_signature(record)
        actual_mode = _weight_mode(original)
        if actual_mode == "disabled":
            return True
        if actual_mode != mode:
            _report_once(
                f"mode-drift:{key}",
                f"weight shape changed before mutation at {key}; filtering this graph is disabled",
            )
            return False

    filtered = _filtered_signature(original, mode)
    live = record["pool"].BalancedItems[record["index"]].Weight

    try:
        live.BaseValueConstant = 0.0
        if mode == "attribute":
            live.BaseValueScale = 0.0
    except Exception as exc:
        # We own this immediate write attempt; restore the fields we just touched.
        try:
            live.BaseValueConstant = float(original[0])
            if mode == "attribute":
                live.BaseValueScale = float(original[6])
        except Exception:
            pass
        _report_once(
            f"apply-write:{key}",
            f"failed to filter {key}: {type(exc).__name__}: {exc}",
         )
        return False

    candidate = {
        **record,
        "mode": mode,
        "original": original,
        "filtered": filtered,
    }
    if _current_signature(candidate) != filtered:
        try:
            live.BaseValueConstant = float(original[0])
            if mode == "attribute":
                live.BaseValueScale = float(original[6])
        except Exception:
            pass
        _report_once(
            f"apply-verify:{key}",
            f"filtered weight did not match expected signature at {key}",
         )
        return False

    _managed[key] = candidate
    return True


def _plan_desired_mutations() -> tuple[dict[tuple[str, int, str, str], tuple[dict[str, Any], str]], str | None]:
    desired: dict[tuple[str, int, str, str], tuple[dict[str, Any], str]] = {}
    leaf_available: dict[tuple[str, int, str], bool] = {}

    for leaf_id, record in _leaf_records.items():
        owned = _owned(record["balance_path"])
        if owned is None:
            return {}, f"ownership unresolved for {record['balance_path']}"
        if not owned:
            # Respect an entry which was already disabled by another mod before our
            # scan. Unknown positive shapes remain untouched and count as reachable.
            original = _original_for(record)
            leaf_available[leaf_id] = _weight_mode(original) != "disabled"
            continue

        key = _entry_key(record)
        if key in _blocked_keys:
            return {}, f"externally conflicted owned leaf {record['balance_path']}"

        original = _original_for(record)
        mode = _weight_mode(original)
        if mode == "disabled":
            leaf_available[leaf_id] = False
            continue
        if mode not in ("constant", "attribute"):
            return {}, (
                f"unsupported owned leaf weight shape at {record['pool_path']}"
                f"[{record['index']}] {record['balance_path']}"
            )

        desired[key] = (record, mode)
        leaf_available[leaf_id] = False

    memo: dict[str, bool] = {}
    visiting: set[str] = set()

    def pool_available(pool_path: str) -> bool:
        if pool_path in memo:
            return memo[pool_path]
        if pool_path in visiting:
            raise RuntimeError(f"cycle while evaluating {pool_path}")
        visiting.add(pool_path)

        node = _pool_nodes.get(pool_path)
        if node is None:
            raise RuntimeError(f"missing pool node {pool_path}")

        any_available = False
        for record in node["entries"]:
            if record["child_path"] is None:
                leaf_id = (record["pool_path"], record["index"], record["balance_path"])
                if leaf_available.get(leaf_id, False):
                    any_available = True
                continue

            child_available = pool_available(record["child_path"])
            if child_available:
                # The subtree has an eligible leaf, but an edge which was already
                # disabled before our scan is still not reachable from this parent.
                edge_mode = _weight_mode(_original_for(record))
                if edge_mode != "disabled":
                    any_available = True
                continue

            # Child is exhausted for this source. Disable only this exact parent edge.
            key = _entry_key(record)
            if key in _blocked_keys:
                raise RuntimeError(f"externally conflicted exhausted edge {key}")
            original = _original_for(record)
            mode = _weight_mode(original)
            if mode == "disabled":
                continue
            if mode not in ("constant", "attribute"):
                raise RuntimeError(f"unsupported exhausted-edge weight shape at {key}")
            desired[key] = (record, mode)

        visiting.remove(pool_path)
        memo[pool_path] = any_available
        return any_available

    try:
        pool_available(WORLD_POOL_PATH)
    except RuntimeError as exc:
        return {}, str(exc)

    return desired, None


def _reconcile() -> bool:
    desired, blocker = _plan_desired_mutations()
    if blocker is not None:
        _report_once(f"plan-blocker:{blocker}", f"filter plan rejected: {blocker}")
        _restore_all()
        return False

    desired_keys = set(desired)

    # Restore entries which are no longer owned/exhausted before applying new filters.
    for key, record in list(_managed.items()):
        if key not in desired_keys:
            _restore_record(key, record)

    # Apply leaves/edges selected by the current source-local ownership plan.
    for key, (record, mode) in desired.items():
        if not _apply_record(record, mode):
            _restore_all()
            return False

    return True


def _refresh() -> None:
    global _graph_ready

    if not _graph_ready:
        if not _collect_graph():
            _restore_all()
            return
        if not _rebuild_customization_map():
            _graph_ready = False
            _restore_all()
            return
    else:
        wanted = {record["balance_path"] for record in _leaf_records.values()}
        if wanted.difference(_customization_by_balance):
            if not _rebuild_customization_map():
                _restore_all()
                return

    global _startup_reported

    if not _reconcile():
        return

    if not _startup_reported:
        owned_leaves = 0
        for record in _leaf_records.values():
            try:
                if _owned(record["balance_path"]) is True:
                    owned_leaves += 1
            except Exception:
                pass

        filtered_leaves = sum(1 for key in _managed if key[2] == "leaf")
        exhausted_edges = sum(1 for key in _managed if key[2] == "edge")
        logging.info(
            "[NoDuplicateCosmetics] READY candidate=0.1.2 "
            f"pools={len(_pool_nodes)} leaves={len(_leaf_records)} "
            f"mapped={len(_customization_by_balance)} owned={owned_leaves} "
            f"filtered_leaves={filtered_leaves} exhausted_edges={exhausted_edges} "
            f"blocked={len(_blocked_keys)}"
        )
        _startup_reported = True


def _player_identity() -> tuple[str, int | None] | None:
    try:
        pc = get_pc()
        if pc is None or pc.Pawn is None:
            return None
        try:
            if pc.Pawn.IsActorBeingDestroyed():
                return None
        except Exception:
            pass
        return _path(pc), getattr(pc, "InternalIndex", None)
    except Exception:
        return None


@hook(HUD_FRAME, Type.POST)
def _hud_frame(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _pc_identity, _ready_since, _last_refresh, _graph_ready

    now = time.monotonic()
    identity = _player_identity()
    if identity is None:
        _ready_since = None
        return

    if _pc_identity != identity:
        # A different local controller/profile context must never inherit a stale
        # ownership plan. Restore what we own, then rebuild lazily for the new player.
        _restore_all()
        _pc_identity = identity
        _ready_since = now
        _last_refresh = 0.0
        _graph_ready = False
        _customization_by_balance.clear()
        return

    if _ready_since is None:
        _ready_since = now
        return
    if now - _ready_since < PLAYER_SETTLE_SECONDS:
        return
    if now - _last_refresh < REFRESH_INTERVAL_SECONDS:
        return
    _last_refresh = now

    try:
        _refresh()
    except Exception as exc:
        _report_once(
            f"refresh-exception:{type(exc).__name__}:{exc}",
            f"refresh failed closed: {type(exc).__name__}: {exc}",
        )
        _restore_all()


def on_enable() -> None:
    global _root_pool, _graph_ready, _pc_identity, _ready_since, _last_refresh
    global _startup_reported

    _root_pool = None
    _graph_ready = False
    _pool_nodes.clear()
    _leaf_records.clear()
    _customization_by_balance.clear()
    _managed.clear()
    _blocked_keys.clear()
    _reported_errors.clear()
    _pc_identity = None
    _ready_since = None
    _last_refresh = 0.0
    _startup_reported = False
    logging.info("[NoDuplicateCosmetics] ENABLED candidate=0.1.2 waiting_for_player")


def on_disable() -> None:
    _restore_all()


mod = build_mod(on_enable=on_enable, on_disable=on_disable)
