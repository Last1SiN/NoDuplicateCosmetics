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

logging.info("[NoDuplicateCosmetics] LOADED candidate=0.2.0")

HUD_FRAME = "/Script/Engine.HUD:ReceiveDrawHUD"

PLAYER_SETTLE_SECONDS = 2.0
REFRESH_INTERVAL_SECONDS = 1.0
DISCOVERY_INTERVAL_SECONDS = 5.0

_graph_ready = False
_pool_nodes: dict[str, dict[str, Any]] = {}
_cosmetic_leaf_records: dict[tuple[str, int, str], dict[str, Any]] = {}
_customization_by_balance: dict[str, tuple[str, UObject]] = {}

_managed: dict[tuple[str, int, str, str], dict[str, Any]] = {}
_blocked_keys: set[tuple[str, int, str, str]] = set()

_pc_identity: tuple[str, int | None] | None = None
_ready_since: float | None = None
_last_refresh = 0.0
_last_discovery = 0.0

_reported_errors: set[str] = set()
_startup_reported = False
_last_topology_summary: tuple[int, int, int, int] | None = None


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


def _candidate_path(value: Any) -> str:
    if value is None:
        return "<None>"

    path = _path(value)
    if path != "<unreadable-path>":
        return path

    try:
        text = str(value)
    except Exception:
        return "<unreadable>"

    match = re.search(r"(/Game/[^\'\"\s>)]+)", text)
    return match.group(1) if match else text


def _find_loaded_object(class_name: str, path: str) -> UObject | None:
    if not path.startswith("/Game/"):
        return None
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception:
        return None


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
    target_kind = "edge" if record["kind"] == "child" else "leaf"
    target = record["child_path"] if target_kind == "edge" else record["balance_path"]
    return record["pool_path"], record["index"], target_kind, target


def _current_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    return _weight_signature(record["pool"].BalancedItems[record["index"]].Weight)


def _original_for(record: dict[str, Any]) -> tuple[Any, ...]:
    managed = _managed.get(_entry_key(record))
    if managed is not None:
        return managed["original"]
    return _current_signature(record)


def _entry_enabled(record: dict[str, Any]) -> bool:
    try:
        return _weight_mode(_original_for(record)) != "disabled"
    except Exception as exc:
        _report_once(
            f"weight-read:{_entry_key(record)}",
            f"could not inspect weight at {_entry_key(record)}; leaving it reachable: "
            f"{type(exc).__name__}: {exc}",
        )
        return True


def _rebuild_customization_map() -> bool:
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
                balance_path = _candidate_path(candidate.BalanceData)
            except Exception:
                continue
            if balance_path.startswith("/Game/"):
                mapping[balance_path] = (kind, candidate)

    _customization_by_balance.clear()
    _customization_by_balance.update(mapping)
    return True


def _entry_balance_info(entry: Any) -> tuple[str, str]:
    selected_value: Any = None
    balance_path = "<unresolved>"

    for name in ("ResolvedInventoryBalanceData", "InventoryBalanceData"):
        try:
            value = getattr(entry, name)
        except Exception:
            continue

        path = _candidate_path(value)
        if path in ("<None>", "<unreadable>", "<unreadable-path>"):
            continue

        selected_value = value
        balance_path = path
        break

    if not balance_path.startswith("/Game/"):
        return balance_path, "unknown"

    if balance_path in _customization_by_balance:
        return balance_path, "cosmetic"

    if _is_a(selected_value, "CustomizationInventoryBalanceData"):
        return balance_path, "cosmetic_unmapped"
    if _is_a(selected_value, "InventoryBalanceData"):
        return balance_path, "noncosmetic"

    cosmetic = _find_loaded_object("CustomizationInventoryBalanceData", balance_path)
    if cosmetic is not None:
        return balance_path, "cosmetic_unmapped"

    base = _find_loaded_object("InventoryBalanceData", balance_path)
    if base is not None:
        return balance_path, "noncosmetic"

    return balance_path, "unknown"


def _entry_child_info(entry: Any, loaded_pools: dict[str, UObject]) -> tuple[str, UObject | None]:
    try:
        value = entry.ItemPoolData
    except Exception:
        return "<None>", None

    if value is None:
        return "<None>", None

    path = _candidate_path(value)
    if not path.startswith("/Game/"):
        return path, None

    if _is_a(value, "ItemPoolData"):
        return path, value

    return path, loaded_pools.get(path)


def _restore_record(key: tuple[str, int, str, str], record: dict[str, Any]) -> bool:
    try:
        current = _current_signature(record)
    except Exception as exc:
        _managed.pop(key, None)
        _blocked_keys.add(key)
        _report_once(
            f"restore-read:{key}",
            f"managed entry became unreadable; dropping ownership for {key}: "
            f"{type(exc).__name__}: {exc}",
        )
        return False

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

    try:
        live = record["pool"].BalancedItems[record["index"]].Weight
        live.BaseValueConstant = float(original[0])
        if record["mode"] == "attribute":
            live.BaseValueScale = float(original[6])
    except Exception as exc:
        _report_once(
            f"restore-write:{key}",
            f"failed to restore {key}: {type(exc).__name__}: {exc}",
        )
        return False

    try:
        restored = _current_signature(record) == original
    except Exception:
        restored = False

    if not restored:
        _report_once(
            f"restore-verify:{key}",
            f"restored weight did not match captured signature at {key}",
        )
        return False

    _managed.pop(key, None)
    return True


def _restore_all() -> None:
    for key, record in list(_managed.items()):
        _restore_record(key, record)


def _apply_record(record: dict[str, Any], mode: str) -> bool:
    key = _entry_key(record)

    if key in _blocked_keys:
        return False

    existing = _managed.get(key)
    if existing is not None:
        existing["pool"] = record["pool"]
        existing["index"] = record["index"]

        try:
            current = _current_signature(existing)
        except Exception as exc:
            _blocked_keys.add(key)
            _managed.pop(key, None)
            _report_once(
                f"managed-read:{key}",
                f"managed entry became unreadable; filtering disabled for {key}: "
                f"{type(exc).__name__}: {exc}",
            )
            return False

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
        try:
            original = _current_signature(record)
        except Exception as exc:
            _report_once(
                f"apply-read:{key}",
                f"could not inspect {key}; leaving vanilla value untouched: "
                f"{type(exc).__name__}: {exc}",
            )
            return False

        actual_mode = _weight_mode(original)
        if actual_mode == "disabled":
            return True
        if actual_mode != mode:
            _report_once(
                f"mode-drift:{key}",
                f"weight shape changed before mutation at {key}; leaving it untouched",
            )
            return False

    filtered = _filtered_signature(original, mode)

    try:
        live = record["pool"].BalancedItems[record["index"]].Weight
        live.BaseValueConstant = 0.0
        if mode == "attribute":
            live.BaseValueScale = 0.0
    except Exception as exc:
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

    try:
        verified = _current_signature(candidate) == filtered
    except Exception:
        verified = False

    if not verified:
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


def _discover_loaded_graph() -> bool:
    global _graph_ready, _last_topology_summary

    if not _rebuild_customization_map():
        return False

    try:
        candidates = list(unrealsdk.find_all("ItemPoolData", exact=False))
    except Exception as exc:
        _report_once(
            "find-all:ItemPoolData",
            f"could not enumerate loaded ItemPoolData: {type(exc).__name__}: {exc}",
        )
        return False

    loaded_pools: dict[str, UObject] = {}
    for pool in candidates:
        pool_path = _path(pool)
        if pool_path.startswith("/Game/"):
            loaded_pools[pool_path] = pool

    new_nodes: dict[str, dict[str, Any]] = {}
    new_cosmetic_leaves: dict[tuple[str, int, str], dict[str, Any]] = {}

    for pool_path, pool in loaded_pools.items():
        try:
            count = len(pool.BalancedItems)
        except Exception as exc:
            _report_once(
                f"pool-read:{pool_path}",
                f"could not read BalancedItems for {pool_path}; leaving pool unmanaged: "
                f"{type(exc).__name__}: {exc}",
            )
            continue

        records: list[dict[str, Any]] = []

        for idx in range(count):
            try:
                live = pool.BalancedItems[idx]
            except Exception:
                continue

            child_path, child = _entry_child_info(live, loaded_pools)
            if child_path.startswith("/Game/"):
                record = {
                    "kind": "child",
                    "pool": pool,
                    "pool_path": pool_path,
                    "index": idx,
                    "child": child,
                    "child_path": child_path,
                    "balance_path": None,
                    "balance_kind": None,
                }
                records.append(record)
                continue

            balance_path, balance_kind = _entry_balance_info(live)
            record = {
                "kind": "leaf",
                "pool": pool,
                "pool_path": pool_path,
                "index": idx,
                "child": None,
                "child_path": None,
                "balance_path": balance_path,
                "balance_kind": balance_kind,
            }
            records.append(record)

            if balance_kind in ("cosmetic", "cosmetic_unmapped"):
                new_cosmetic_leaves[(pool_path, idx, balance_path)] = record

        new_nodes[pool_path] = {
            "pool": pool,
            "entries": records,
        }

    for key, managed in list(_managed.items()):
        if key[0] not in new_nodes:
            _restore_record(key, managed)

    _pool_nodes.clear()
    _pool_nodes.update(new_nodes)
    _cosmetic_leaf_records.clear()
    _cosmetic_leaf_records.update(new_cosmetic_leaves)
    _graph_ready = bool(_pool_nodes)

    mapped_cosmetic = sum(
        1 for record in _cosmetic_leaf_records.values()
        if record["balance_kind"] == "cosmetic"
    )
    unmapped_cosmetic = len(_cosmetic_leaf_records) - mapped_cosmetic

    summary = (
        len(_pool_nodes),
        len(_cosmetic_leaf_records),
        mapped_cosmetic,
        unmapped_cosmetic,
    )

    if _last_topology_summary is not None and summary != _last_topology_summary:
        logging.info(
            "[NoDuplicateCosmetics] TOPOLOGY_REFRESH candidate=0.2.0 "
            f"loaded_pools={summary[0]} cosmetic_leaves={summary[1]} "
            f"mapped_cosmetic={summary[2]} unmapped_cosmetic={summary[3]}"
        )

    _last_topology_summary = summary
    return _graph_ready


def _owned(balance_path: str, ownership_cache: dict[str, bool | None]) -> bool | None:
    if balance_path in ownership_cache:
        return ownership_cache[balance_path]

    mapped = _customization_by_balance.get(balance_path)
    if mapped is None:
        ownership_cache[balance_path] = None
        return None

    kind, data = mapped
    try:
        pc = get_pc()
        if pc is None:
            ownership_cache[balance_path] = None
            return None

        if kind == "OakCustomizationData":
            value = bool(pc.IsCustomizationUnlocked(data))
        elif kind == "OakInventoryCustomizationPartData":
            value = bool(pc.IsInventoryCustomizationPartUnlocked(data))
        elif kind == "CrewQuartersDecorationItemData":
            value = bool(pc.IsCrewQuartersDecorationUnlocked(data))
        else:
            value = None
    except Exception as exc:
        _report_once(
            f"ownership:{kind}:{balance_path}",
            f"ownership query failed for {balance_path}: {type(exc).__name__}: {exc}",
        )
        value = None

    ownership_cache[balance_path] = value
    return value


def _plan_desired_mutations() -> tuple[
    dict[tuple[str, int, str, str], tuple[dict[str, Any], str]],
    dict[str, int],
]:
    desired: dict[tuple[str, int, str, str], tuple[dict[str, Any], str]] = {}
    leaf_state: dict[tuple[str, int, str], tuple[bool, bool, bool]] = {}

    ownership_cache: dict[str, bool | None] = {}
    stats = {
        "owned": 0,
        "filtered_leaf_candidates": 0,
        "exhausted_edge_candidates": 0,
        "unmapped": 0,
        "ownership_unresolved": 0,
        "unsupported_owned": 0,
        "cycles": 0,
    }

    for leaf_id, record in _cosmetic_leaf_records.items():
        balance_path = record["balance_path"]

        if record["balance_kind"] == "cosmetic_unmapped":
            stats["unmapped"] += 1
            leaf_state[leaf_id] = (_entry_enabled(record), True, False)
            continue

        owned = _owned(balance_path, ownership_cache)
        if owned is None:
            stats["ownership_unresolved"] += 1
            leaf_state[leaf_id] = (_entry_enabled(record), True, False)
            continue

        try:
            original = _original_for(record)
            mode = _weight_mode(original)
        except Exception as exc:
            _report_once(
                f"leaf-weight:{leaf_id}",
                f"could not inspect cosmetic leaf {balance_path}; leaving it reachable: "
                f"{type(exc).__name__}: {exc}",
            )
            leaf_state[leaf_id] = (True, True, False)
            continue

        if not owned:
            leaf_state[leaf_id] = (mode != "disabled", True, False)
            continue

        stats["owned"] += 1
        key = _entry_key(record)

        if key in _blocked_keys:
            leaf_state[leaf_id] = (mode != "disabled", True, False)
            continue

        if mode == "disabled":
            leaf_state[leaf_id] = (False, True, False)
            continue

        if mode not in ("constant", "attribute"):
            stats["unsupported_owned"] += 1
            leaf_state[leaf_id] = (True, True, False)
            _report_once(
                f"unsupported-owned:{key}",
                f"unsupported owned cosmetic weight; leaving vanilla eligibility at {key}",
            )
            continue

        desired[key] = (record, mode)
        stats["filtered_leaf_candidates"] += 1
        leaf_state[leaf_id] = (False, True, True)

    memo: dict[str, tuple[bool, bool, bool]] = {}
    visiting: set[str] = set()

    def pool_state(pool_path: str) -> tuple[bool, bool, bool]:
        if pool_path in memo:
            return memo[pool_path]

        if pool_path in visiting:
            stats["cycles"] += 1
            _report_once(
                f"cycle:{pool_path}",
                f"cycle detected in loaded item-pool graph at {pool_path}; "
                "cycle kept reachable and unmanaged",
            )
            return True, False, False

        node = _pool_nodes.get(pool_path)
        if node is None:
            return True, False, False

        visiting.add(pool_path)

        any_available = False
        cosmetic_only = True
        affected = False
        saw_entry = False

        for record in node["entries"]:
            saw_entry = True

            if record["kind"] == "child":
                edge_enabled = _entry_enabled(record)
                child_path = record["child_path"]

                if record["child"] is None or child_path not in _pool_nodes:
                    if edge_enabled:
                        any_available = True
                    cosmetic_only = False
                    continue

                child_available, child_cosmetic_only, child_affected = pool_state(child_path)
                affected = affected or child_affected

                if not child_cosmetic_only:
                    cosmetic_only = False

                if child_available:
                    if edge_enabled:
                        any_available = True
                    continue

                if child_cosmetic_only and child_affected:
                    key = _entry_key(record)

                    if key in _blocked_keys:
                        continue

                    try:
                        original = _original_for(record)
                        mode = _weight_mode(original)
                    except Exception as exc:
                        _report_once(
                            f"edge-weight:{key}",
                            f"could not inspect exhausted child edge {key}; "
                            f"leaving parent edge untouched: {type(exc).__name__}: {exc}",
                        )
                        continue

                    if mode == "disabled":
                        continue

                    if mode in ("constant", "attribute"):
                        desired[key] = (record, mode)
                        stats["exhausted_edge_candidates"] += 1
                    else:
                        _report_once(
                            f"unsupported-edge:{key}",
                            f"unsupported exhausted-child edge weight; "
                            f"leaving parent edge untouched at {key}",
                        )
                continue

            balance_kind = record["balance_kind"]

            if balance_kind in ("cosmetic", "cosmetic_unmapped"):
                leaf_id = (
                    record["pool_path"],
                    record["index"],
                    record["balance_path"],
                )
                leaf_available, _is_cosmetic, leaf_affected = leaf_state.get(
                    leaf_id,
                    (True, True, False),
                )
                if leaf_available:
                    any_available = True
                affected = affected or leaf_affected
                continue

            cosmetic_only = False
            if _entry_enabled(record):
                any_available = True

        visiting.remove(pool_path)

        if not saw_entry:
            cosmetic_only = False

        result = (any_available, cosmetic_only, affected)
        memo[pool_path] = result
        return result

    for pool_path in list(_pool_nodes):
        pool_state(pool_path)

    return desired, stats


def _reconcile() -> dict[str, int] | None:
    desired, stats = _plan_desired_mutations()
    desired_keys = set(desired)

    for key, record in list(_managed.items()):
        if key not in desired_keys:
            _restore_record(key, record)

    applied_leaf = 0
    applied_edge = 0

    for key, (record, mode) in desired.items():
        if _apply_record(record, mode):
            if key[2] == "leaf":
                applied_leaf += 1
            else:
                applied_edge += 1

    stats["filtered_leaves"] = applied_leaf
    stats["exhausted_edges"] = applied_edge
    stats["blocked"] = len(_blocked_keys)
    return stats


def _refresh(now: float) -> None:
    global _last_discovery, _startup_reported

    if (
        not _graph_ready
        or _last_discovery == 0.0
        or now - _last_discovery >= DISCOVERY_INTERVAL_SECONDS
    ):
        _last_discovery = now
        if not _discover_loaded_graph():
            _restore_all()
            return

    stats = _reconcile()
    if stats is None:
        return

    if not _startup_reported:
        mapped_cosmetic = sum(
            1 for record in _cosmetic_leaf_records.values()
            if record["balance_kind"] == "cosmetic"
        )
        unmapped_cosmetic = len(_cosmetic_leaf_records) - mapped_cosmetic

        logging.info(
            "[NoDuplicateCosmetics] READY candidate=0.2.0 "
            f"loaded_pools={len(_pool_nodes)} "
            f"cosmetic_leaves={len(_cosmetic_leaf_records)} "
            f"mapped_cosmetic={mapped_cosmetic} "
            f"unmapped_cosmetic={unmapped_cosmetic} "
            f"owned={stats['owned']} "
            f"filtered_leaves={stats['filtered_leaves']} "
            f"exhausted_edges={stats['exhausted_edges']} "
            f"unsupported_owned={stats['unsupported_owned']} "
            f"ownership_unresolved={stats['ownership_unresolved']} "
            f"blocked={stats['blocked']} "
            f"cycles={stats['cycles']}"
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
    global _pc_identity, _ready_since, _last_refresh, _last_discovery
    global _graph_ready, _startup_reported, _last_topology_summary

    now = time.monotonic()
    identity = _player_identity()

    if identity is None:
        _ready_since = None
        return

    if _pc_identity != identity:
        _restore_all()

        _pc_identity = identity
        _ready_since = now
        _last_refresh = 0.0
        _last_discovery = 0.0
        _graph_ready = False
        _startup_reported = False
        _last_topology_summary = None

        _pool_nodes.clear()
        _cosmetic_leaf_records.clear()
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
        _refresh(now)
    except Exception as exc:
        _report_once(
            f"refresh-exception:{type(exc).__name__}:{exc}",
            f"refresh failed closed: {type(exc).__name__}: {exc}",
        )
        _restore_all()


def on_enable() -> None:
    global _graph_ready, _pc_identity, _ready_since, _last_refresh, _last_discovery
    global _startup_reported, _last_topology_summary

    _restore_all()

    _graph_ready = False
    _pool_nodes.clear()
    _cosmetic_leaf_records.clear()
    _customization_by_balance.clear()
    _managed.clear()
    _blocked_keys.clear()
    _reported_errors.clear()

    _pc_identity = None
    _ready_since = None
    _last_refresh = 0.0
    _last_discovery = 0.0
    _startup_reported = False
    _last_topology_summary = None

    logging.info(
        "[NoDuplicateCosmetics] ENABLED candidate=0.2.0 "
        "scope=loaded-item-pool-graphs waiting_for_player"
    )


def on_disable() -> None:
    _restore_all()


mod = build_mod(on_enable=on_enable, on_disable=on_disable)
