from __future__ import annotations

from typing import Any

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook, keybind
from unrealsdk import logging, make_struct
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmeticsProbe supports Borderlands 3 only"

SPAWN_LOOT_ASYNC = "/Script/OakGame.OakBlueprintLibrary:SpawnLootAsync"
ACTIVATE_PICKUP = "/Script/GbxInventory.InventoryItemPickup:ActivatePickup"
BALANCE_POST_BEGIN_PLAY = "/Script/GbxInventory.InventoryBalanceStateComponent:PostBeginPlay"

STANDARD_ENEMY_LIST = (
    "/Game/GameData/Loot/ItemPools/ItemPoolList_StandardEnemyGunsandGear."
    "ItemPoolList_StandardEnemyGunsandGear"
)

POOLS: dict[str, tuple[str, str]] = {
    "world_cosmetics": (
        "ItemPoolData",
        "/Game/GameData/Loot/ItemPools/ItemPool_SkinsAndMisc.ItemPool_SkinsAndMisc",
    ),
    "heads": (
        "ItemPoolData",
        "/Game/Pickups/Customizations/_Design/ItemPools/Heads/"
        "ItemPool_Customizations_Heads_Loot.ItemPool_Customizations_Heads_Loot",
    ),
    "skins": (
        "ItemPoolData",
        "/Game/Pickups/Customizations/_Design/ItemPools/Skins/"
        "ItemPool_Customizations_Skins_Loot.ItemPool_Customizations_Skins_Loot",
    ),
    "weapon_skins": (
        "ItemPoolData",
        "/Game/Gear/WeaponSkins/_Design/ItemPools/"
        "ItemPool_Customizations_WeaponSkins_Loot.ItemPool_Customizations_WeaponSkins_Loot",
    ),
    "trinkets": (
        "ItemPoolData",
        "/Game/Gear/WeaponTrinkets/_Design/ItemPools/"
        "ItemPool_Customizations_WeaponTrinkets_Loot.ItemPool_Customizations_WeaponTrinkets_Loot",
    ),
    "echo": (
        "ItemPoolData",
        "/Game/PlayerCharacters/_Customizations/EchoDevice/ItemPools/"
        "ItemPool_Customizations_Echo_Loot.ItemPool_Customizations_Echo_Loot",
    ),
    "room_deco": (
        "ItemPoolData",
        "/Game/Pickups/Customizations/_Design/ItemPools/PlayerRoomDeco/"
        "ItemPool_Customizations_RoomDeco_Loot.ItemPool_Customizations_RoomDeco_Loot",
    ),
}

_seen_pickups: set[str] = set()
_seen_states: set[str] = set()
_oak_blueprint_library: UObject | None = None
_active_batch_label = "<none>"


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


def _package_from_object_path(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _load_object(class_name: str, path: str) -> UObject | None:
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] load_package failed for {path}: {exc}")
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] find_object failed for {path}: {exc}")
        return None


def _initializer_text(value: Any) -> str:
    if value is None:
        return "<None>"
    fields: list[str] = []
    for name in (
        "BaseValueConstant",
        "BaseValueScale",
        "BaseValueAttribute",
        "AttributeInitializer",
        "DataTableValue",
    ):
        try:
            fields.append(f"{name}={getattr(value, name)!r}")
        except Exception:
            pass
    return "{" + ", ".join(fields) + "}"


def _dump_pool_data(label: str, pool: UObject) -> None:
    try:
        entries = list(pool.BalancedItems)
    except Exception as exc:
        logging.info(f"[NoDuplicateCosmeticsProbe] POOL {label}: no readable BalancedItems: {exc}")
        return
    try:
        quantity = _initializer_text(pool.Quantity)
    except Exception:
        quantity = "<unreadable>"
    logging.info(
        f"[NoDuplicateCosmeticsProbe] POOL {label} path={_path(pool)} "
        f"balanced_count={len(entries)} quantity={quantity}"
    )
    for idx, entry in enumerate(entries):
        try:
            child_pool = entry.ItemPoolData
        except Exception:
            child_pool = None
        try:
            balance = entry.InventoryBalanceData
        except Exception:
            balance = None
        try:
            resolved = entry.ResolvedInventoryBalanceData
        except Exception:
            resolved = None
        try:
            weight = _initializer_text(entry.Weight)
        except Exception:
            weight = "<unreadable>"
        logging.info(
            "[NoDuplicateCosmeticsProbe] POOL_ENTRY "
            f"label={label} idx={idx} child_pool={_path(child_pool)} "
            f"balance={_path(balance)} resolved={_path(resolved)} weight={weight}"
        )


def _dump_topology() -> None:
    pool_list = _load_object("ItemPoolListData", STANDARD_ENEMY_LIST)
    if pool_list is None:
        return
    try:
        entries = list(pool_list.ItemPools)
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] standard enemy ItemPools unreadable: {exc}")
        return

    logging.info(
        "[NoDuplicateCosmeticsProbe] TOPOLOGY standard_enemy "
        f"path={_path(pool_list)} entry_count={len(entries)}"
    )
    for idx, entry in enumerate(entries):
        try:
            child = entry.ItemPool
        except Exception:
            child = None
        try:
            probability = _initializer_text(entry.PoolProbability)
        except Exception:
            probability = "<unreadable>"
        try:
            selections = _initializer_text(entry.NumberOfTimesToSelectFromThisPool)
        except Exception:
            selections = "<unreadable>"
        logging.info(
            "[NoDuplicateCosmeticsProbe] TOPOLOGY_ENTRY "
            f"idx={idx} pool={_path(child)} probability={probability} selections={selections}"
        )

    for label in ("world_cosmetics", "heads", "skins", "weapon_skins", "trinkets", "echo", "room_deco"):
        pool = _load_object(*POOLS[label])
        if pool is not None:
            _dump_pool_data(label, pool)


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


def _is_customization_inventory_data(obj: Any) -> bool:
    return _is_a(obj, "CustomizationInventoryData")


def _is_customization_balance(balance: Any) -> bool:
    return _is_a(balance, "CustomizationInventoryBalanceData")


def _match_customization_data(balance: UObject) -> tuple[str, UObject | None]:
    try:
        for candidate in unrealsdk.find_all("OakCustomizationData", exact=False):
            try:
                if candidate.BalanceData is balance or _path(candidate.BalanceData) == _path(balance):
                    return "OakCustomizationData", candidate
            except Exception:
                continue
    except Exception:
        pass

    try:
        for candidate in unrealsdk.find_all("OakInventoryCustomizationPartData", exact=False):
            try:
                if candidate.BalanceData is balance or _path(candidate.BalanceData) == _path(balance):
                    return "OakInventoryCustomizationPartData", candidate
            except Exception:
                continue
    except Exception:
        pass

    try:
        for candidate in unrealsdk.find_all("CrewQuartersDecorationItemData", exact=False):
            try:
                if candidate.BalanceData is balance or _path(candidate.BalanceData) == _path(balance):
                    return "CrewQuartersDecorationItemData", candidate
            except Exception:
                continue
    except Exception:
        pass

    return "<unmatched>", None


def _owned(kind: str, data: UObject | None) -> str:
    if data is None:
        return "UNKNOWN"
    try:
        pc = get_pc()
    except Exception:
        return "NO_PC"
    if pc is None:
        return "NO_PC"
    try:
        if kind == "OakCustomizationData":
            return "YES" if bool(pc.IsCustomizationUnlocked(data)) else "NO"
        if kind == "OakInventoryCustomizationPartData":
            return "YES" if bool(pc.IsInventoryCustomizationPartUnlocked(data)) else "NO"
        if kind == "CrewQuartersDecorationItemData":
            return "YES" if bool(pc.IsCrewQuartersDecorationUnlocked(data)) else "NO"
    except Exception as exc:
        return f"ERROR:{exc}"
    return "UNKNOWN"


def _inspect_balance(state: UObject, source: str) -> bool:
    try:
        balance = state.GetInventoryBalanceData()
    except Exception:
        return False
    try:
        inv_data = state.GetInventoryData()
    except Exception:
        inv_data = None
    if not (_is_customization_inventory_data(inv_data) or _is_customization_balance(balance)):
        return False

    kind, custom_data = _match_customization_data(balance)
    ownership = _owned(kind, custom_data)
    try:
        display_name = str(state.GetDisplayName())
    except Exception:
        display_name = "<unreadable>"
    try:
        custom_parts = [_path(x) for x in state.GetCustomizationPartList()]
    except Exception:
        custom_parts = []

    logging.info(
        "[NoDuplicateCosmeticsProbe] COSMETIC "
        f"source={source} name={display_name!r} balance={_path(balance)} "
        f"balance_class={_class_name(balance)} "
        f"inventory_data={_path(inv_data)} inventory_class={_class_name(inv_data)} "
        f"match_kind={kind} customization={_path(custom_data)} owned={ownership} "
        f"custom_parts={custom_parts}"
    )
    return True


def _scan_loaded_customization_states(source: str) -> tuple[int, int]:
    try:
        states = list(unrealsdk.find_all("InventoryBalanceStateComponent", exact=False))
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] state scan failed: {exc}")
        return 0, 0
    total = len(states)
    cosmetics = 0
    for state in states:
        try:
            if _inspect_balance(state, source):
                cosmetics += 1
        except Exception as exc:
            logging.error(
                f"[NoDuplicateCosmeticsProbe] state inspection failed for {_path(state)}: {exc}"
            )
    logging.info(
        f"[NoDuplicateCosmeticsProbe] STATE_SCAN source={source} total={total} cosmetics={cosmetics}"
    )
    return total, cosmetics


def _spawn_pool(label: str, count: int) -> None:
    global _oak_blueprint_library, _active_batch_label
    spec = POOLS.get(label)
    if spec is None:
        logging.error(f"[NoDuplicateCosmeticsProbe] unknown pool label {label}")
        return
    pool = _load_object(*spec)
    if pool is None:
        return
    try:
        pc = get_pc()
        pawn = pc.Pawn
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] no local pawn for spawn: {exc}")
        return
    if pawn is None:
        logging.error("[NoDuplicateCosmeticsProbe] no local pawn for spawn")
        return

    if _oak_blueprint_library is None:
        try:
            _oak_blueprint_library = unrealsdk.find_class("OakBlueprintLibrary").ClassDefaultObject
        except Exception as exc:
            logging.error(f"[NoDuplicateCosmeticsProbe] OakBlueprintLibrary unavailable: {exc}")
            return

    try:
        request = make_struct(
            "SpawnDroppedPickupLootRequest",
            ContextActor=pawn,
            ItemPools=pool,
        )
    except Exception as exc:
        logging.error(f"[NoDuplicateCosmeticsProbe] could not build spawn request: {exc}")
        return

    _active_batch_label = label
    logging.info(
        f"[NoDuplicateCosmeticsProbe] DEV_SPAWN label={label} count={count} pool={_path(pool)}"
    )
    for _ in range(count):
        try:
            _oak_blueprint_library.SpawnLootAsync(pawn, request)
        except Exception as exc:
            logging.error(f"[NoDuplicateCosmeticsProbe] SpawnLootAsync failed: {exc}")
            break


@keybind(
    "Scan Loaded Cosmetic States",
    "NumPadZero",
    display_name="Scan loaded cosmetic balance states",
    description="Logs all currently loaded cosmetic InventoryBalanceStateComponent objects.",
)
def _kb_scan_states() -> None:
    _scan_loaded_customization_states("manual_scan")


@keybind(
    "Dump Loot Topology",
    "NumPadOne",
    display_name="Dump standard enemy + cosmetic pool topology",
    description="Logs standard enemy pool entries and the world cosmetic sub-pools.",
)
def _kb_dump_topology() -> None:
    _dump_topology()


@keybind("Spawn World Cosmetics x20", "NumPadTwo")
def _kb_world() -> None:
    _spawn_pool("world_cosmetics", 20)


@keybind("Spawn Heads x10", "NumPadThree")
def _kb_heads() -> None:
    _spawn_pool("heads", 10)


@keybind("Spawn Skins x10", "NumPadFour")
def _kb_skins() -> None:
    _spawn_pool("skins", 10)


@keybind("Spawn Weapon Skins x10", "NumPadFive")
def _kb_weapon_skins() -> None:
    _spawn_pool("weapon_skins", 10)


@keybind("Spawn Trinkets x10", "NumPadSix")
def _kb_trinkets() -> None:
    _spawn_pool("trinkets", 10)


@keybind("Spawn ECHO Themes x10", "NumPadSeven")
def _kb_echo() -> None:
    _spawn_pool("echo", 10)


@keybind("Spawn Room Decorations x10", "NumPadEight")
def _kb_room_deco() -> None:
    _spawn_pool("room_deco", 10)


@hook(SPAWN_LOOT_ASYNC, Type.PRE)
def _spawn_loot_async(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    try:
        request = args.Request
    except Exception:
        return
    try:
        pool = request.ItemPools
    except Exception:
        pool = None
    try:
        selected = list(request.SelectedInventoryInfos)
    except Exception:
        selected = []
    if selected:
        balances: list[str] = []
        for info in selected:
            try:
                balances.append(_path(info.InventoryBalanceData))
            except Exception:
                balances.append("<unreadable>")
        logging.info(
            "[NoDuplicateCosmeticsProbe] SpawnLootAsync "
            f"pool={_path(pool)} selected_count={len(selected)} selected_balances={balances}"
        )


@hook(BALANCE_POST_BEGIN_PLAY, Type.POST)
def _balance_post_begin_play(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    key = _path(obj)
    if key in _seen_states:
        return
    try:
        if _inspect_balance(obj, f"state_post_begin_play:batch={_active_batch_label}"):
            _seen_states.add(key)
    except Exception as exc:
        logging.error(
            f"[NoDuplicateCosmeticsProbe] PostBeginPlay inspection failed for {key}: {exc}"
        )


@hook(ACTIVATE_PICKUP, Type.POST)
def _activate_pickup(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    key = _path(obj)
    if key in _seen_pickups:
        return
    try:
        if not obj.IsPickupInitialized():
            return
    except Exception:
        pass
    try:
        state = obj.GetInventoryBalanceStateComponent()
    except Exception:
        state = None
    if state is None:
        return
    _seen_pickups.add(key)
    _inspect_balance(state, f"pickup:{key}")


mod = build_mod()
