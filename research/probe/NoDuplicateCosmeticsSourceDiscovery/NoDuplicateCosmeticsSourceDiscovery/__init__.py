from __future__ import annotations

from typing import Any
import re
import time

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook
from unrealsdk import logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmeticsSourceDiscovery supports Borderlands 3 only"

HUD_FRAME = "/Script/Engine.HUD:ReceiveDrawHUD"

PLAYER_SETTLE_SECONDS = 3.0
SCAN_INTERVAL_SECONDS = 10.0

_enabled = False
_ready_since: float | None = None
_last_scan = 0.0
_scan_index = 0

_seen_sources: set[tuple[str, str, str, str]] = set()
_seen_pool_assets: set[str] = set()
_reported_errors: set[str] = set()

# Static item-pool graphs do not change during ordinary play. Store only plain data,
# never UObject references, so map transitions / GC cannot leave stale object handles.
_pool_analysis_cache: dict[str, dict[str, Any]] = {}


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
    logging.error(f"[NDCSourceDiscovery] {message}")


def _package_from_object_path(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _load_object(class_name: str, path: str) -> UObject | None:
    if not path.startswith("/Game/"):
        return None
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception:
        pass
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception:
        return None


def _candidate_path(value: Any) -> str:
    if value is None:
        return "<None>"

    p = _path(value)
    if p != "<unreadable-path>":
        return p

    # Soft object pointers stringify with an asset path even if not loaded.
    try:
        text = str(value)
    except Exception:
        return "<unreadable>"

    match = re.search(r"(/Game/[^\'\"\s>)]+)", text)
    return match.group(1) if match else text


def _resolve_pool(value: Any) -> UObject | None:
    if value is None:
        return None
    if _is_a(value, "ItemPoolData"):
        return value
    path = _candidate_path(value)
    if path.startswith("/Game/"):
        return _load_object("ItemPoolData", path)
    return None


def _entry_balance_path(entry: Any) -> str:
    for name in ("ResolvedInventoryBalanceData", "InventoryBalanceData"):
        try:
            value = getattr(entry, name)
        except Exception:
            continue
        path = _candidate_path(value)
        if path not in ("<None>", "<unreadable>", "<unreadable-path>"):
            return path
    return "<unresolved>"


def _entry_child_pool(entry: Any) -> UObject | None:
    try:
        return _resolve_pool(entry.ItemPoolData)
    except Exception:
        return None


def _load_balance(path: str) -> UObject | None:
    if not path.startswith("/Game/"):
        return None

    obj = _load_object("CustomizationInventoryBalanceData", path)
    if obj is not None:
        return obj

    # Used only to distinguish cosmetic vs non-cosmetic leaves.
    return _load_object("InventoryBalanceData", path)


def _merge_analysis(dst: dict[str, Any], src: dict[str, Any]) -> None:
    dst["pools"].update(src["pools"])
    dst["children"].update(src["children"])
    dst["cosmetic"] += src["cosmetic"]
    dst["noncosmetic"] += src["noncosmetic"]
    dst["unresolved"] += src["unresolved"]


def _analyze_pool(pool: UObject, visiting: set[str] | None = None) -> dict[str, Any]:
    pool_path = _path(pool)

    cached = _pool_analysis_cache.get(pool_path)
    if cached is not None:
        return {
            "pools": set(cached["pools"]),
            "children": set(cached["children"]),
            "cosmetic": int(cached["cosmetic"]),
            "noncosmetic": int(cached["noncosmetic"]),
            "unresolved": int(cached["unresolved"]),
        }

    if visiting is None:
        visiting = set()
    if pool_path in visiting:
        return {
            "pools": {pool_path},
            "children": set(),
            "cosmetic": 0,
            "noncosmetic": 0,
            "unresolved": 1,
        }

    visiting.add(pool_path)
    result = {
        "pools": {pool_path},
        "children": set(),
        "cosmetic": 0,
        "noncosmetic": 0,
        "unresolved": 0,
    }

    try:
        entries = list(pool.BalancedItems)
    except Exception as exc:
        result["unresolved"] += 1
        _report_once(
            f"balanced-items:{pool_path}",
            f"POOL_READ_FAIL pool={pool_path} error={type(exc).__name__}:{exc}",
        )
        visiting.remove(pool_path)
        return result

    for entry in entries:
        child = _entry_child_pool(entry)
        if child is not None:
            child_path = _path(child)
            if not child_path.startswith("/Game/"):
                result["unresolved"] += 1
                continue
            result["children"].add(child_path)
            child_result = _analyze_pool(child, visiting)
            _merge_analysis(result, child_result)
            continue

        balance_path = _entry_balance_path(entry)
        if not balance_path.startswith("/Game/"):
            result["unresolved"] += 1
            continue

        balance = _load_balance(balance_path)
        if balance is None:
            result["unresolved"] += 1
        elif _is_a(balance, "CustomizationInventoryBalanceData"):
            result["cosmetic"] += 1
        else:
            result["noncosmetic"] += 1

    visiting.remove(pool_path)

    # Cache a plain-data copy.
    _pool_analysis_cache[pool_path] = {
        "pools": tuple(sorted(result["pools"])),
        "children": tuple(sorted(result["children"])),
        "cosmetic": result["cosmetic"],
        "noncosmetic": result["noncosmetic"],
        "unresolved": result["unresolved"],
    }
    return result


def _classify(info: dict[str, Any]) -> str | None:
    cosmetics = int(info["cosmetic"])
    noncosmetics = int(info["noncosmetic"])
    pool_count = len(info["pools"])

    if cosmetics <= 0:
        return None
    if noncosmetics > 0:
        return "mixed_cosmetic_noncosmetic"
    if pool_count > 1:
        return "nested_cosmetic"
    return "dedicated_cosmetic"


def _family(path: str) -> str:
    match = re.match(r"^/Game/PatchDLC/([^/]+)", path)
    if match:
        return f"PatchDLC:{match.group(1)}"
    if path.startswith("/Game/"):
        return "base"
    return "unknown"


def _emit_source(
    kind: str,
    owner: Any,
    field: str,
    pool: UObject | None,
) -> bool:
    if pool is None:
        return False

    pool_path = _path(pool)
    if not pool_path.startswith("/Game/"):
        return False

    info = _analyze_pool(pool)
    topology = _classify(info)
    if topology is None:
        return False

    owner_path = owner if isinstance(owner, str) else _path(owner)
    key = (kind, owner_path, field, pool_path)
    if key in _seen_sources:
        return False

    _seen_sources.add(key)

    logging.info(
        "[NDCSourceDiscovery] SOURCE "
        f"kind={kind} "
        f"owner={owner_path} "
        f"field={field} "
        f"pool={pool_path} "
        f"family={_family(pool_path)} "
        f"topology={topology} "
        f"pools={len(info['pools'])} "
        f"cosmetic_leaves={info['cosmetic']} "
        f"noncosmetic_leaves={info['noncosmetic']} "
        f"unresolved={info['unresolved']}"
    )
    return True


def _find_all(class_name: str) -> list[Any]:
    try:
        return list(unrealsdk.find_all(class_name, exact=False))
    except Exception as exc:
        _report_once(
            f"find-all:{class_name}",
            f"FIND_ALL_FAIL class={class_name} error={type(exc).__name__}:{exc}",
        )
        return []


def _scan_item_pool_list(
    owner: Any,
    source_kind: str,
    list_obj: Any,
    field_prefix: str,
    seen_lists: set[str] | None = None,
) -> int:
    if list_obj is None:
        return 0
    if seen_lists is None:
        seen_lists = set()

    list_path = _path(list_obj)
    if list_path in seen_lists:
        return 0
    seen_lists.add(list_path)

    new_count = 0

    try:
        infos = list(list_obj.ItemPools)
    except Exception:
        infos = []

    for idx, info in enumerate(infos):
        try:
            pool = _resolve_pool(info.ItemPool)
        except Exception:
            pool = None
        if _emit_source(
            source_kind,
            owner,
            f"{field_prefix}.ItemPools[{idx}]",
            pool,
        ):
            new_count += 1

    try:
        included = list(list_obj.ItemPoolIncludedLists)
    except Exception:
        included = []

    for idx, nested in enumerate(included):
        new_count += _scan_item_pool_list(
            owner,
            source_kind,
            nested,
            f"{field_prefix}.ItemPoolIncludedLists[{idx}]",
            seen_lists,
        )

    return new_count


def _scan_collection(owner: Any, source_kind: str, collection: Any, field: str) -> int:
    if collection is None:
        return 0

    new_count = 0

    try:
        infos = list(collection.ItemPools)
    except Exception:
        infos = []

    for idx, info in enumerate(infos):
        try:
            pool = _resolve_pool(info.ItemPool)
        except Exception:
            pool = None
        if _emit_source(
            source_kind,
            owner,
            f"{field}.ItemPools[{idx}]",
            pool,
        ):
            new_count += 1

    try:
        lists = list(collection.ItemPoolLists)
    except Exception:
        lists = []

    for idx, list_obj in enumerate(lists):
        new_count += _scan_item_pool_list(
            owner,
            source_kind,
            list_obj,
            f"{field}.ItemPoolLists[{idx}]",
        )

    return new_count


def _scan_loot_configurations(
    owner: Any,
    source_kind: str,
    configs: Any,
    field: str,
) -> int:
    try:
        configs = list(configs)
    except Exception:
        return 0

    new_count = 0
    for cidx, config in enumerate(configs):
        try:
            attachments = list(config.ItemAttachments)
        except Exception:
            attachments = []

        for aidx, attachment in enumerate(attachments):
            try:
                pool = _resolve_pool(attachment.ItemPool)
            except Exception:
                pool = None

            if _emit_source(
                source_kind,
                owner,
                f"{field}[{cidx}].ItemAttachments[{aidx}]",
                pool,
            ):
                new_count += 1

    return new_count


def _scan_mission_rewards() -> int:
    new_count = 0
    seen: set[str] = set()

    # Base-class enumeration is preferred; explicit subclasses are fallbacks for
    # SDK/class-reflection builds where the abstract base is not enumerable.
    for class_name in (
        "OakBaseMissionRewardData",
        "OakMissionRewardData",
        "OakOptionalObjectiveRewardData",
    ):
        for reward in _find_all(class_name):
            path = _path(reward)
            if path in seen:
                continue
            seen.add(path)

            try:
                pool = _resolve_pool(reward.ItemPoolReward)
            except Exception:
                pool = None

            if _emit_source(
                "mission_reward",
                reward,
                "ItemPoolReward",
                pool,
            ):
                new_count += 1

    return new_count


def _scan_ai_death_sources() -> int:
    new_count = 0
    for component in _find_all("AIBalanceStateComponent"):
        for field in (
            "DropOnDeathItemPools",
            "CharacterExpansionDropOnDeathItemPools",
        ):
            try:
                collection = getattr(component, field)
            except Exception:
                continue
            new_count += _scan_collection(
                component,
                "ai_death",
                collection,
                field,
            )
    return new_count


def _scan_lootable_balances() -> int:
    new_count = 0

    for balance in _find_all("LootableBalanceData"):
        try:
            default_loot = balance.DefaultLoot
        except Exception:
            default_loot = []
        new_count += _scan_loot_configurations(
            balance,
            "lootable_balance",
            default_loot,
            "DefaultLoot",
        )

        try:
            included_lists = list(balance.DefaultIncludedLootLists)
        except Exception:
            included_lists = []

        for idx, loot_list in enumerate(included_lists):
            try:
                loot_data = loot_list.LootData
            except Exception:
                loot_data = []
            new_count += _scan_loot_configurations(
                balance,
                "lootable_balance",
                loot_data,
                f"DefaultIncludedLootLists[{idx}].LootData",
            )

    return new_count


def _scan_loot_lists() -> int:
    new_count = 0
    for loot_list in _find_all("LootListData"):
        try:
            loot_data = loot_list.LootData
        except Exception:
            loot_data = []

        new_count += _scan_loot_configurations(
            loot_list,
            "loot_list",
            loot_data,
            "LootData",
        )

    return new_count


def _scan_runtime_lootables() -> int:
    new_count = 0
    for component in _find_all("LootableComponent"):
        try:
            configs = component.LootConfigurations
        except Exception:
            configs = []

        new_count += _scan_loot_configurations(
            component,
            "lootable_runtime",
            configs,
            "LootConfigurations",
        )

    return new_count


def _scan_pool_assets() -> int:
    analyses: dict[str, dict[str, Any]] = {}

    for pool in _find_all("ItemPoolData"):
        path = _path(pool)
        if not path.startswith("/Game/"):
            continue
        info = _analyze_pool(pool)
        if int(info["cosmetic"]) > 0:
            analyses[path] = info

    if not analyses:
        return 0

    # A top-level candidate is not referenced as a child by another loaded cosmetic pool.
    cosmetic_children: set[str] = set()
    for info in analyses.values():
        cosmetic_children.update(
            child for child in info["children"] if child in analyses
        )

    new_count = 0
    for path in sorted(analyses):
        if path in cosmetic_children:
            continue
        if path in _seen_pool_assets:
            continue

        info = analyses[path]
        topology = _classify(info)
        if topology is None:
            continue

        _seen_pool_assets.add(path)
        logging.info(
            "[NDCSourceDiscovery] POOL_CANDIDATE "
            f"pool={path} "
            f"family={_family(path)} "
            f"topology={topology} "
            f"pools={len(info['pools'])} "
            f"cosmetic_leaves={info['cosmetic']} "
            f"noncosmetic_leaves={info['noncosmetic']} "
            f"unresolved={info['unresolved']} "
            "owner=UNRESOLVED"
        )
        new_count += 1

    return new_count


def _player_ready() -> bool:
    try:
        pc = get_pc()
        if pc is None or pc.Pawn is None:
            return False
        try:
            if pc.Pawn.IsActorBeingDestroyed():
                return False
        except Exception:
            pass
        return True
    except Exception:
        return False


def _run_scan() -> None:
    global _scan_index

    _scan_index += 1
    before_sources = len(_seen_sources)
    before_candidates = len(_seen_pool_assets)

    new_mission = _scan_mission_rewards()
    new_ai = _scan_ai_death_sources()
    new_lootable_balance = _scan_lootable_balances()
    new_loot_list = _scan_loot_lists()
    new_runtime_lootable = _scan_runtime_lootables()
    _scan_pool_assets()

    new_sources = len(_seen_sources) - before_sources
    new_candidates = len(_seen_pool_assets) - before_candidates

    if _scan_index == 1 or new_sources > 0 or new_candidates > 0:
        logging.info(
            "[NDCSourceDiscovery] SCAN_SUMMARY "
            f"scan={_scan_index} "
            f"new_sources={new_sources} "
            f"total_sources={len(_seen_sources)} "
            f"new_pool_candidates={new_candidates} "
            f"total_pool_candidates={len(_seen_pool_assets)} "
            f"new_mission={new_mission} "
            f"new_ai={new_ai} "
            f"new_lootable_balance={new_lootable_balance} "
            f"new_loot_list={new_loot_list} "
            f"new_runtime_lootable={new_runtime_lootable} "
            f"errors={len(_reported_errors)}"
        )


@hook(HUD_FRAME, Type.POST)
def _hud_frame(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _ready_since, _last_scan

    if not _enabled:
        return

    now = time.monotonic()

    if not _player_ready():
        _ready_since = None
        return

    if _ready_since is None:
        _ready_since = now
        return

    if now - _ready_since < PLAYER_SETTLE_SECONDS:
        return

    if _last_scan != 0.0 and now - _last_scan < SCAN_INTERVAL_SECONDS:
        return

    _last_scan = now

    try:
        _run_scan()
    except Exception as exc:
        _report_once(
            f"scan-exception:{type(exc).__name__}:{exc}",
            f"SCAN_FAIL error={type(exc).__name__}:{exc}",
        )


def on_enable() -> None:
    global _enabled, _ready_since, _last_scan, _scan_index

    _enabled = True
    _ready_since = None
    _last_scan = 0.0
    _scan_index = 0

    _seen_sources.clear()
    _seen_pool_assets.clear()
    _reported_errors.clear()
    _pool_analysis_cache.clear()

    logging.info(
        "[NDCSourceDiscovery] ENABLED version=0.1.0 "
        "mode=read-only "
        f"scan_interval={SCAN_INTERVAL_SECONDS:.0f}s"
    )


def on_disable() -> None:
    global _enabled
    _enabled = False


logging.info(
    "[NDCSourceDiscovery] LOADED version=0.1.0 "
    "mutation=NONE spawn=NONE"
)

mod = build_mod(on_enable=on_enable, on_disable=on_disable)
