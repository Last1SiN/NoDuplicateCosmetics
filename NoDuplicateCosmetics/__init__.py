from __future__ import annotations

from typing import Any
import re
import time

import unrealsdk
from mods_base import MODS_DIR, Game, build_mod, get_pc, hook
from unrealsdk import logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmetics supports Borderlands 3 only"


HUD_FRAME = "/Script/Engine.HUD:ReceiveDrawHUD"
UNLOCK_CUSTOMIZATION = "/Script/OakGame.OakPlayerController:ClientUnlockCustomization"
UNLOCK_INVENTORY_CUSTOMIZATION = (
    "/Script/OakGame.OakPlayerController:ClientUnlockInventoryCustomizationPart"
)
UNLOCK_ROOM_DECORATION = (
    "/Script/OakGame.OakPlayerController:ClientUnlockCrewQuartersDecoration"
)

BALANCE_SET_GAME_STAGE = (
    "/Script/GbxGameSystemCore.BalanceStateComponent:SetGameStage"
)
LOOTABLE_INITIALIZE = (
    "/Script/GbxInventory.LootableComponent:InitializeLootConfigurations"
)
MISSION_COMPLETE = "/Script/GbxMission.Mission:CompleteMission"
SPAWN_LOOT = "/Script/OakGame.OakBlueprintLibrary:SpawnLoot"
SPAWN_LOOT_ASYNC = "/Script/OakGame.OakBlueprintLibrary:SpawnLootAsync"

PLAYER_SETTLE_SECONDS = 2.0
WORLD_TRANSITION_SETTLE_SECONDS = 5.0
UNLOCK_RECONCILE_DELAY_SECONDS = 0.15
SOURCE_REDISCOVERY_DELAY_SECONDS = 0.05

_graph_ready = False
_pool_nodes: dict[str, dict[str, Any]] = {}
_cosmetic_leaf_records: dict[tuple[str, int, str], dict[str, Any]] = {}
_customization_by_balance: dict[str, tuple[str, UObject]] = {}

# Entries currently owned by this mod. Each managed record captures the exact live
# pool/index plus before/after weight signatures. Restoration is guarded: a later
# third-party value is never overwritten.
_managed: dict[tuple[str, int, str, str], dict[str, Any]] = {}
_blocked_keys: set[tuple[str, int, str, str]] = set()

_pc_identity: tuple[Any, ...] | None = None
_ready_since: float | None = None
_refresh_pending = False
_refresh_due = 0.0
_refresh_needs_discovery = False

_reported_errors: set[str] = set()

PERF_DIAG_BUILD = "perf1"
PERF_FRAME_GAP_MS = 20.0
_perf_log_path = MODS_DIR / "NoDuplicateCosmetics_perf.log"
_perf_log_handle: Any = None
_perf_seq = 0
_perf_last_frame: float | None = None


def _perf_open() -> None:
    global _perf_log_handle, _perf_seq, _perf_last_frame

    try:
        if _perf_log_handle is not None:
            _perf_log_handle.close()
    except Exception:
        pass

    _perf_log_handle = None
    _perf_seq = 0
    _perf_last_frame = None

    try:
        _perf_log_handle = _perf_log_path.open(
            "w",
            encoding="utf-8",
            buffering=1,
        )
    except Exception:
        _perf_log_handle = None

    _perf_log(
        "DIAG_START",
        f"build={PERF_DIAG_BUILD} frame_gap_threshold_ms={PERF_FRAME_GAP_MS:.1f}",
    )


def _perf_close() -> None:
    global _perf_log_handle

    handle = _perf_log_handle
    _perf_log_handle = None
    if handle is None:
        return

    try:
        handle.flush()
        handle.close()
    except Exception:
        pass


def _perf_log(event: str, details: str = "") -> None:
    global _perf_seq

    handle = _perf_log_handle
    if handle is None:
        return

    _perf_seq += 1
    stamp = time.perf_counter()
    suffix = f" {details}" if details else ""

    try:
        handle.write(f"{_perf_seq:06d} t={stamp:.6f} {event}{suffix}\n")
    except Exception:
        pass


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
    pool = record.get("pool")
    if pool is None:
        raise RuntimeError("managed pool reference is detached")
    return _weight_signature(pool.BalancedItems[record["index"]].Weight)


def _detach_managed_live_refs() -> None:
    # A Python UObject wrapper may outlive the underlying UE object during travel.
    # Never carry those wrappers across a Pawn/HUD context change: native access to
    # a stale wrapper can AV before Python can raise/catch an exception.
    for record in _managed.values():
        record["pool"] = None
        if "child" in record:
            record["child"] = None


def _original_for(record: dict[str, Any]) -> tuple[Any, ...]:
    managed = _managed.get(_entry_key(record))
    if managed is not None:
        return managed["original"]
    return _current_signature(record)


def _entry_enabled(record: dict[str, Any]) -> bool:
    try:
        return _weight_mode(_original_for(record)) != "disabled"
    except Exception as exc:
        # Unknown/unreadable entries remain reachable. This is deliberately fail-open
        # locally so the generalized candidate never suppresses a foreign branch merely
        # because it could not inspect its weight.
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
    """
    Returns (balance_path, classification).

    classification:
      cosmetic          — loaded customization balance with a proven ownership mapping
      cosmetic_unmapped — loaded customization balance but no supported mapping object
      noncosmetic       — loaded inventory balance not derived from customization
      unknown           — unresolved/unloaded balance; must remain reachable
    """
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
    if record.get("pool") is None:
        _managed.pop(key, None)
        return True

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
    global _graph_ready

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

    # Rebind managed records to current-world pool wrappers. A pool absent from
    # new_nodes is no longer loaded, so there is no live object to restore. Drop
    # its bookkeeping without touching the detached old-world UObject wrapper.
    for key, managed in list(_managed.items()):
        node = new_nodes.get(key[0])
        if node is None:
            _managed.pop(key, None)
            continue
        managed["pool"] = node["pool"]
        managed["index"] = key[1]
        if "child" in managed:
            managed["child"] = None

    _pool_nodes.clear()
    _pool_nodes.update(new_nodes)
    _cosmetic_leaf_records.clear()
    _cosmetic_leaf_records.update(new_cosmetic_leaves)
    _graph_ready = bool(_pool_nodes)

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

    # availability tuple:
    # (currently_can_produce_result, is_cosmetic_leaf, affected_by_our_filter)
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
        # (available_any, cosmetic_only, affected_by_our_filter)
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
                    # The referenced child is not currently loaded. Keep the branch
                    # reachable and do not claim the parent is cosmetic-only.
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

                # Only propagate exhaustion through a child which is entirely cosmetic
                # and became exhausted at least partly because of this mod's filtering.
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

            # Direct non-cosmetic or unresolved leaves are never mutated. They keep a
            # mixed/unknown graph from being classified cosmetic-only.
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

    # Restore entries which are no longer owned/exhausted.
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



def _known_pool_path(path: str) -> bool:
    return path.startswith("/Game/") and path in _pool_nodes


def _value_is_unknown_loaded_pool(value: Any) -> bool:
    if value is None:
        return False

    path = _candidate_path(value)
    if not path.startswith("/Game/"):
        return False

    if _known_pool_path(path):
        return False

    if _is_a(value, "ItemPoolData"):
        return True

    loaded = _find_loaded_object("ItemPoolData", path)
    return loaded is not None and not _known_pool_path(path)


def _item_pool_list_has_unknown_loaded_pool(
    value: Any,
    seen: set[str] | None = None,
) -> bool:
    if value is None:
        return False

    if seen is None:
        seen = set()

    path = _candidate_path(value)
    if path in seen:
        return False
    seen.add(path)

    if _value_is_unknown_loaded_pool(value):
        return True

    # ItemPoolListData exposes ItemPools plus ItemPoolIncludedLists. Some runtime
    # wrappers/builds have historically surfaced alternate field names, so keep
    # the reads defensive without forcing package loads.
    for field in ("ItemPools",):
        try:
            infos = list(getattr(value, field))
        except Exception:
            infos = []

        for info in infos:
            try:
                pool_value = info.ItemPool
            except Exception:
                continue

            if _value_is_unknown_loaded_pool(pool_value):
                return True

    for field in (
        "ItemPoolIncludedLists",
        "IncludedItemPoolLists",
        "ItemPoolLists",
    ):
        try:
            nested_lists = list(getattr(value, field))
        except Exception:
            nested_lists = []

        for nested in nested_lists:
            if _item_pool_list_has_unknown_loaded_pool(nested, seen):
                return True

    return False


def _collection_has_unknown_loaded_pool(collection: Any) -> bool:
    if collection is None:
        return False

    try:
        infos = list(collection.ItemPools)
    except Exception:
        infos = []

    for info in infos:
        try:
            pool_value = info.ItemPool
        except Exception:
            continue

        if _value_is_unknown_loaded_pool(pool_value):
            return True

    try:
        lists = list(collection.ItemPoolLists)
    except Exception:
        lists = []

    for list_value in lists:
        if _item_pool_list_has_unknown_loaded_pool(list_value):
            return True

    return False


def _ai_source_has_unknown_loaded_pool(obj: UObject) -> bool:
    if not _is_a(obj, "AIBalanceStateComponent"):
        return False

    for field in (
        "DropOnDeathItemPools",
        "CharacterExpansionDropOnDeathItemPools",
    ):
        try:
            collection = getattr(obj, field)
        except Exception:
            continue

        if _collection_has_unknown_loaded_pool(collection):
            return True

    return False


def _lootable_has_unknown_loaded_pool(obj: UObject) -> bool:
    try:
        configurations = list(obj.LootConfigurations)
    except Exception:
        configurations = []

    for configuration in configurations:
        try:
            attachments = list(configuration.ItemAttachments)
        except Exception:
            attachments = []

        for attachment in attachments:
            try:
                pool_value = attachment.ItemPool
            except Exception:
                continue

            if _value_is_unknown_loaded_pool(pool_value):
                return True

    return False


def _mission_has_unknown_loaded_reward_pool(obj: UObject) -> bool:
    try:
        reward_data = obj.RewardData
    except Exception:
        return False

    if reward_data is None:
        return False

    try:
        reward_pool = reward_data.ItemPoolReward
    except Exception:
        return False

    return _value_is_unknown_loaded_pool(reward_pool)


def _schedule_source_rediscovery_if_needed(needed: bool) -> None:
    if needed:
        _schedule_refresh(SOURCE_REDISCOVERY_DELAY_SECONDS, discover=True)


def _refresh_unknown_source_now_if_needed(
    item_pools: Any,
    origin: str,
) -> None:
    # Last-chance synchronous guard for native SpawnLoot: if the actual source
    # root is loaded but not yet present in our graph, rebuild+reconcile before
    # native stock selection proceeds.
    check_started = time.perf_counter()
    unknown = _item_pool_list_has_unknown_loaded_pool(item_pools)
    check_ms = (time.perf_counter() - check_started) * 1000.0

    if not unknown:
        if check_ms >= 2.0:
            _perf_log(
                "SOURCE_CHECK_SLOW",
                f"origin={origin} unknown=False check_ms={check_ms:.3f}",
            )
        return

    _perf_log(
        "SOURCE_UNKNOWN",
        f"origin={origin} check_ms={check_ms:.3f}",
    )

    refresh_started = time.perf_counter()
    try:
        _refresh_once(discover=True, origin=origin)
    except Exception as exc:
        _report_once(
            f"source-refresh:{type(exc).__name__}:{exc}",
            f"source-triggered refresh failed closed: {type(exc).__name__}: {exc}",
        )
        _restore_all()
    finally:
        total_ms = (time.perf_counter() - refresh_started) * 1000.0
        _perf_log(
            "SOURCE_REFRESH_DONE",
            f"origin={origin} total_ms={total_ms:.3f}",
        )


def _refresh_once(discover: bool, origin: str = "unknown") -> None:
    total_started = time.perf_counter()
    discover_ms = 0.0

    if discover or not _graph_ready:
        discover_started = time.perf_counter()
        discovered = _discover_loaded_graph()
        discover_ms = (time.perf_counter() - discover_started) * 1000.0

        if not discovered:
            _restore_all()
            total_ms = (time.perf_counter() - total_started) * 1000.0
            _perf_log(
                "REFRESH",
                (
                    f"origin={origin} discover={discover} discovered=False "
                    f"discover_ms={discover_ms:.3f} reconcile_ms=0.000 "
                    f"total_ms={total_ms:.3f} pools={len(_pool_nodes)} "
                    f"leaves={len(_cosmetic_leaf_records)} managed={len(_managed)}"
                ),
            )
            return

    reconcile_started = time.perf_counter()
    stats = _reconcile()
    reconcile_ms = (time.perf_counter() - reconcile_started) * 1000.0
    total_ms = (time.perf_counter() - total_started) * 1000.0

    _perf_log(
        "REFRESH",
        (
            f"origin={origin} discover={discover} discovered=True "
            f"discover_ms={discover_ms:.3f} reconcile_ms={reconcile_ms:.3f} "
            f"total_ms={total_ms:.3f} pools={len(_pool_nodes)} "
            f"leaves={len(_cosmetic_leaf_records)} managed={len(_managed)}"
        ),
    )

    if stats is None:
        return

def _schedule_refresh(delay_seconds: float, discover: bool) -> None:
    global _refresh_pending, _refresh_due, _refresh_needs_discovery

    due = time.monotonic() + max(0.0, float(delay_seconds))

    if not _refresh_pending:
        _refresh_pending = True
        _refresh_due = due
    else:
        _refresh_due = min(_refresh_due, due)

    _refresh_needs_discovery = _refresh_needs_discovery or discover



def _player_identity(hud: UObject) -> tuple[Any, ...] | None:
    try:
        pc = get_pc()
        if pc is None or pc.Pawn is None:
            return None

        try:
            if pc.Pawn.IsActorBeingDestroyed():
                return None
        except Exception:
            pass

        return (
            _path(pc),
            getattr(pc, "InternalIndex", None),
            _path(pc.Pawn),
            getattr(pc.Pawn, "InternalIndex", None),
            _path(hud),
            getattr(hud, "InternalIndex", None),
        )
    except Exception:
        return None



@hook(BALANCE_SET_GAME_STAGE, Type.POST)
def _balance_set_game_stage_hook(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # Cheap source-aware check only. Full discovery happens only when a newly
    # loaded AI death-loot root is actually observed.
    started = time.perf_counter()
    needed = _ai_source_has_unknown_loaded_pool(obj)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if needed or elapsed_ms >= 2.0:
        _perf_log(
            "AI_SOURCE_CHECK",
            (
                f"needed={needed} check_ms={elapsed_ms:.3f} "
                f"path={_path(obj)}"
            ),
        )

    _schedule_source_rediscovery_if_needed(needed)


@hook(LOOTABLE_INITIALIZE, Type.POST)
def _lootable_initialize_hook(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # LootableComponent materializes its loot configurations before use. Trigger
    # rediscovery only if those configurations reference an unknown loaded pool.
    started = time.perf_counter()
    needed = _lootable_has_unknown_loaded_pool(obj)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if needed or elapsed_ms >= 2.0:
        _perf_log(
            "LOOTABLE_SOURCE_CHECK",
            (
                f"needed={needed} check_ms={elapsed_ms:.3f} "
                f"path={_path(obj)}"
            ),
        )

    _schedule_source_rediscovery_if_needed(needed)


@hook(MISSION_COMPLETE, Type.PRE)
def _mission_complete_hook(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # Mission rewards are infrequent. If the reward pool is already loaded and
    # new to this runtime graph, rebuild synchronously before mission completion
    # can resolve the reward.
    if not _mission_has_unknown_loaded_reward_pool(obj):
        return

    try:
        _refresh_once(discover=True, origin="MissionComplete")
    except Exception as exc:
        _report_once(
            f"mission-refresh:{type(exc).__name__}:{exc}",
            f"mission source refresh failed closed: {type(exc).__name__}: {exc}",
        )
        _restore_all()


@hook(SPAWN_LOOT_ASYNC, Type.PRE)
def _spawn_loot_async_hook(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # Generic final boundary for native asynchronous loot spawning. The request
    # already contains the exact ItemPools object which stock selection will use,
    # so a genuinely late-loaded source can be discovered and filtered before the
    # native async resolver is entered. This hook never invokes SpawnLootAsync.
    try:
        request = args.Request
        item_pools = request.ItemPools
    except Exception:
        return

    _refresh_unknown_source_now_if_needed(item_pools, "SpawnLootAsync")


@hook(SPAWN_LOOT, Type.PRE)
def _spawn_loot_hook(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # Generic final boundary for native synchronous loot spawning. This hook does
    # not spawn anything itself. Known sources cost only a few pointer/path reads;
    # an expensive graph rebuild occurs only for a genuinely new loaded pool.
    try:
        item_pools = args.ItemPools
    except Exception:
        return

    _refresh_unknown_source_now_if_needed(item_pools, "SpawnLoot")


def _on_native_cosmetic_unlock() -> None:
    # Native unlock RPCs are the same-session ownership-change boundary for the
    # three supported cosmetic families. Reconcile once after the profile update
    # instead of polling every cosmetic and loaded pool once per second.
    _schedule_refresh(UNLOCK_RECONCILE_DELAY_SECONDS, discover=False)


@hook(UNLOCK_CUSTOMIZATION, Type.POST)
def _unlock_customization_hook(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    _on_native_cosmetic_unlock()


@hook(UNLOCK_INVENTORY_CUSTOMIZATION, Type.POST)
def _unlock_inventory_customization_hook(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    _on_native_cosmetic_unlock()


@hook(UNLOCK_ROOM_DECORATION, Type.POST)
def _unlock_room_decoration_hook(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    _on_native_cosmetic_unlock()



@hook(HUD_FRAME, Type.POST)
def _hud_frame(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _pc_identity, _ready_since
    global _graph_ready
    global _refresh_pending, _refresh_due, _refresh_needs_discovery
    global _perf_last_frame

    perf_now = time.perf_counter()
    if _perf_last_frame is not None:
        frame_gap_ms = (perf_now - _perf_last_frame) * 1000.0
        if frame_gap_ms >= PERF_FRAME_GAP_MS:
            _perf_log(
                "FRAME_GAP",
                (
                    f"ms={frame_gap_ms:.3f} pending={_refresh_pending} "
                    f"discover_pending={_refresh_needs_discovery}"
                ),
            )
    _perf_last_frame = perf_now

    now = time.monotonic()
    identity = _player_identity(_obj)

    if identity is None:
        _ready_since = None
        return

    if _pc_identity != identity:
        # A new Pawn/HUD context can arrive while the old world is being torn down.
        # Do not dereference or restore through old-world UObject wrappers here:
        # pyunrealsdk cannot turn every stale native pointer access into a Python
        # exception. Preserve only plain managed metadata and rebind it after the
        # new world has settled.
        had_identity = _pc_identity is not None
        if had_identity:
            _detach_managed_live_refs()

        _pc_identity = identity
        _ready_since = now
        _graph_ready = False

        _pool_nodes.clear()
        _cosmetic_leaf_records.clear()
        _customization_by_balance.clear()

        _refresh_pending = True
        settle = (
            WORLD_TRANSITION_SETTLE_SECONDS
            if had_identity
            else PLAYER_SETTLE_SECONDS
        )
        _refresh_due = now + settle
        _refresh_needs_discovery = True
        return

    if _ready_since is None:
        _ready_since = now
        return

    if not _refresh_pending or now < _refresh_due:
        return

    discover = _refresh_needs_discovery
    _refresh_pending = False
    _refresh_due = 0.0
    _refresh_needs_discovery = False

    try:
        _refresh_once(discover, origin="HUDDeferred")
    except Exception as exc:
        _report_once(
            f"refresh-exception:{type(exc).__name__}:{exc}",
            f"refresh failed closed: {type(exc).__name__}: {exc}",
        )
        _restore_all()



def on_enable() -> None:
    global _graph_ready, _pc_identity, _ready_since
    global _refresh_pending, _refresh_due, _refresh_needs_discovery

    _perf_open()
    _perf_log("ENABLE")
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
    _refresh_pending = False
    _refresh_due = 0.0
    _refresh_needs_discovery = False



def on_disable() -> None:
    _perf_log("DISABLE_BEGIN")
    started = time.perf_counter()
    _restore_all()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    _perf_log("DISABLE_DONE", f"restore_ms={elapsed_ms:.3f}")
    _perf_close()


mod = build_mod(on_enable=on_enable, on_disable=on_disable)
