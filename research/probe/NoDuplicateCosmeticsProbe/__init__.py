from __future__ import annotations

from collections import Counter
from typing import Any
import re

import unrealsdk
from mods_base import Game, build_mod, get_pc, hook
from unrealsdk import logging, make_struct
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

assert Game.get_current() is Game.BL3, "NoDuplicateCosmeticsProbe supports Borderlands 3 only"

BALANCE_POST_BEGIN_PLAY = "/Script/GbxInventory.InventoryBalanceStateComponent:PostBeginPlay"

ECHO_POOL_PATH = (
    "/Game/PlayerCharacters/_Customizations/EchoDevice/ItemPools/"
    "ItemPool_Customizations_Echo_Loot.ItemPool_Customizations_Echo_Loot"
)

REQUESTS = 256

_pool: UObject | None = None
_target_idx: int | None = None
_target_balance_path = ""
_original_sig: tuple[Any, ...] | None = None
_mutation_mode = "none"

_oak_blueprint_library: UObject | None = None

_active_batch = "<none>"
_batch_requests = 0
_batch_observed = 0
_batch_target_hits = 0
_batch_counts: Counter[str] = Counter()

_auto_state = "idle"
_results: dict[str, dict[str, int | float]] = {}
_auto_failed = False


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


def _load_object(class_name: str, path: str) -> UObject | None:
    try:
        unrealsdk.load_package(_package_from_object_path(path))
    except Exception as exc:
        logging.error(f"[NDCAttributeAuto] load_package failed path={path}: {exc}")
    try:
        return unrealsdk.find_object(class_name, path)
    except Exception as exc:
        logging.error(
            f"[NDCAttributeAuto] find_object failed class={class_name} path={path}: {exc}"
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


def _sig_constant_zero(sig: tuple[Any, ...]) -> tuple[Any, ...]:
    return (0.0,) + sig[1:]


def _sig_both_zero(sig: tuple[Any, ...]) -> tuple[Any, ...]:
    return (0.0,) + sig[1:6] + (0.0,)


def _player_ready() -> bool:
    try:
        pc = get_pc()
        return pc is not None and pc.Pawn is not None
    except Exception:
        return False


def _rarity_priority(attribute_path: str) -> int:
    order = (
        "Att_RarityWeight_01_Common",
        "Att_RarityWeight_02_Uncommon",
        "Att_RarityWeight_03_Rare",
        "Att_RarityWeight_04_VeryRare",
        "Att_RarityWeight_05_Legendary",
    )
    for idx, token in enumerate(order):
        if token in attribute_path:
            return idx
    return len(order)


def _build_plan() -> bool:
    global _pool, _target_idx, _target_balance_path, _original_sig

    if _mutation_mode != "none":
        logging.error("[NDCAttributeAuto] PLAN refused while mutation is active")
        return False
    if not _player_ready():
        logging.error("[NDCAttributeAuto] PLAN FAIL-CLOSED: local player/pawn not ready")
        return False

    pool = _load_object("ItemPoolData", ECHO_POOL_PATH)
    if pool is None:
        return False

    try:
        entries = list(pool.BalancedItems)
    except Exception as exc:
        logging.error(f"[NDCAttributeAuto] ECHO pool unreadable: {exc}")
        return False

    candidates: list[tuple[int, str, tuple[Any, ...]]] = []
    for idx in range(len(entries)):
        live = pool.BalancedItems[idx]
        balance = _entry_balance_path(live)
        sig = _weight_signature(live.Weight)
        constant, data_table, _row, _value, base_attr, initializer, scale = sig

        if (
            balance.startswith("/Game/")
            and float(constant) > 0.0
            and data_table == "<None>"
            and base_attr.startswith("/Game/")
            and initializer == "<None>"
            and float(scale) > 0.0
        ):
            candidates.append((idx, balance, sig))

    if not candidates:
        logging.error(
            "[NDCAttributeAuto] PLAN FAIL-CLOSED: no direct ECHO leaf matched "
            "attribute-backed/no-table/no-initializer form"
        )
        return False

    candidates.sort(key=lambda item: (_rarity_priority(str(item[2][4])), item[0]))
    idx, balance, sig = candidates[0]

    _pool = pool
    _target_idx = idx
    _target_balance_path = balance
    _original_sig = sig

    logging.info(
        "[NDCAttributeAuto] PLAN_READY "
        f"entries={len(entries)} target_idx={idx} target={balance} "
        f"attribute={sig[4]} weight=({_weight_text(sig)}) "
        f"candidate_count={len(candidates)}"
    )
    return True


def _target_live_sig() -> tuple[Any, ...] | None:
    if _pool is None or _target_idx is None:
        return None
    try:
        return _weight_signature(_pool.BalancedItems[_target_idx].Weight)
    except Exception as exc:
        logging.error(f"[NDCAttributeAuto] target weight unreadable: {exc}")
        return None


def _verify(label: str, expected: tuple[Any, ...]) -> bool:
    live = _target_live_sig()
    ok = live == expected
    if ok:
        logging.info(
            f"[NDCAttributeAuto] VERIFY PASS label={label} weight=({_weight_text(live)})"
        )
    else:
        logging.error(
            f"[NDCAttributeAuto] VERIFY FAIL label={label} "
            f"expected=({_weight_text(expected)}) "
            f"live=({_weight_text(live) if live else '<None>'})"
        )
    return ok


def _apply_constant_only() -> bool:
    global _mutation_mode
    assert _pool is not None and _target_idx is not None and _original_sig is not None

    if _mutation_mode != "none":
        logging.error(f"[NDCAttributeAuto] constant-only refused mode={_mutation_mode}")
        return False
    if not _verify("before_constant_only", _original_sig):
        return False

    _pool.BalancedItems[_target_idx].Weight.BaseValueConstant = 0.0
    expected = _sig_constant_zero(_original_sig)
    if not _verify("after_constant_only", expected):
        _restore()
        return False

    _mutation_mode = "constant_only"
    logging.info("[NDCAttributeAuto] MUTATION_APPLY PASS mode=constant_only")
    return True


def _apply_both_zero() -> bool:
    global _mutation_mode
    assert _pool is not None and _target_idx is not None and _original_sig is not None

    if _mutation_mode != "none":
        logging.error(f"[NDCAttributeAuto] both-zero refused mode={_mutation_mode}")
        return False
    if not _verify("before_both_zero", _original_sig):
        return False

    live = _pool.BalancedItems[_target_idx].Weight
    live.BaseValueConstant = 0.0
    live.BaseValueScale = 0.0
    expected = _sig_both_zero(_original_sig)
    if not _verify("after_both_zero", expected):
        _restore()
        return False

    _mutation_mode = "both_zero"
    logging.info("[NDCAttributeAuto] MUTATION_APPLY PASS mode=both_zero")
    return True


def _restore() -> bool:
    global _mutation_mode

    if _pool is None or _target_idx is None or _original_sig is None:
        return True

    live = _pool.BalancedItems[_target_idx].Weight
    current = _weight_signature(live)
    allowed = {
        _original_sig,
        _sig_constant_zero(_original_sig),
        _sig_both_zero(_original_sig),
    }
    if current not in allowed:
        logging.error(
            "[NDCAttributeAuto] RESTORE ownership guard conflict; leaving target untouched "
            f"live=({_weight_text(current)})"
        )
        return False

    live.BaseValueConstant = float(_original_sig[0])
    live.BaseValueScale = float(_original_sig[6])

    if _verify("after_restore", _original_sig):
        _mutation_mode = "none"
        logging.info("[NDCAttributeAuto] RESTORE PASS exact signature restored")
        return True
    return False


def _reset_batch(label: str) -> None:
    global _active_batch, _batch_requests, _batch_observed, _batch_target_hits, _batch_counts

    _active_batch = label
    _batch_requests = REQUESTS
    _batch_observed = 0
    _batch_target_hits = 0
    _batch_counts = Counter()


def _spawn(label: str) -> bool:
    global _oak_blueprint_library

    assert _pool is not None
    try:
        pc = get_pc()
        pawn = pc.Pawn
    except Exception as exc:
        logging.error(f"[NDCAttributeAuto] no local pawn: {exc}")
        return False
    if pawn is None:
        logging.error("[NDCAttributeAuto] no local pawn")
        return False

    if _oak_blueprint_library is None:
        try:
            _oak_blueprint_library = unrealsdk.find_class(
                "OakBlueprintLibrary"
            ).ClassDefaultObject
        except Exception as exc:
            logging.error(f"[NDCAttributeAuto] OakBlueprintLibrary unavailable: {exc}")
            return False

    try:
        request = make_struct(
            "SpawnDroppedPickupLootRequest",
            ContextActor=pawn,
            ItemPools=_pool,
        )
    except Exception as exc:
        logging.error(f"[NDCAttributeAuto] request creation failed: {exc}")
        return False

    _reset_batch(label)
    logging.info(
        f"[NDCAttributeAuto] BATCH_START label={label} requests={REQUESTS} "
        f"mutation_mode={_mutation_mode}"
    )
    for _ in range(REQUESTS):
        try:
            _oak_blueprint_library.SpawnLootAsync(pawn, request)
        except Exception as exc:
            logging.error(f"[NDCAttributeAuto] SpawnLootAsync failed: {exc}")
            return False
    return True


def _snapshot_batch(label: str) -> None:
    ratio = (_batch_observed / _batch_requests) if _batch_requests else 0.0
    _results[label] = {
        "requests": _batch_requests,
        "observed": _batch_observed,
        "target_hits": _batch_target_hits,
        "distinct": len(_batch_counts),
        "ratio": ratio,
    }
    logging.info(
        f"[NDCAttributeAuto] BATCH_SUMMARY label={label} "
        f"requests={_batch_requests} observed={_batch_observed} "
        f"observed_ratio={ratio:.4f} target_hits={_batch_target_hits} "
        f"distinct={len(_batch_counts)} mutation_mode={_mutation_mode} "
        f"top={_batch_counts.most_common(15)}"
    )


def _fail(reason: str) -> None:
    global _auto_state, _auto_failed
    _auto_failed = True
    _auto_state = "failed"
    logging.error(f"[NDCAttributeAuto] AUTO_FAIL reason={reason}")
    if _mutation_mode != "none":
        _restore()


def _finish() -> None:
    global _auto_state
    baseline = _results.get("baseline", {})
    constant = _results.get("constant_only", {})
    both = _results.get("both_zero", {})

    baseline_hits = int(baseline.get("target_hits", -1))
    constant_hits = int(constant.get("target_hits", -1))
    both_hits = int(both.get("target_hits", -1))

    if baseline_hits <= 0:
        verdict = "INCONCLUSIVE baseline_target_never_selected"
    elif constant_hits > 0 and both_hits == 0:
        verdict = "PASS constant_only_insufficient both_zero_excludes"
    elif constant_hits == 0 and both_hits == 0:
        verdict = "INCONCLUSIVE constant_only_may_already_exclude"
    else:
        verdict = "REJECT both_zero_did_not_exclude"

    logging.info(
        "[NDCAttributeAuto] AUTO_VERDICT "
        f"{verdict} baseline_hits={baseline_hits} "
        f"constant_only_hits={constant_hits} both_zero_hits={both_hits}"
    )
    _auto_state = "done"


def _start_auto(source: str) -> None:
    global _auto_state

    if _auto_state != "wait_player":
        return
    if not _player_ready():
        return

    logging.info(
        f"[NDCAttributeAuto] PLAYER_READY source={source}; starting automatic sequence"
    )
    if not _build_plan():
        _fail("plan_failed")
        return

    _auto_state = "wait_baseline"
    if not _spawn("baseline"):
        _fail("baseline_spawn_failed")


def _advance_completed_batch() -> None:
    global _auto_state

    if _batch_observed < _batch_requests:
        return

    if _auto_state == "wait_baseline":
        _snapshot_batch("baseline")
        if not _apply_constant_only():
            _fail("constant_only_apply_failed")
            return
        _auto_state = "wait_constant"
        if not _spawn("constant_only"):
            _fail("constant_only_spawn_failed")
        return

    if _auto_state == "wait_constant":
        _snapshot_batch("constant_only")
        if not _restore():
            _fail("constant_only_restore_failed")
            return
        if not _apply_both_zero():
            _fail("both_zero_apply_failed")
            return
        _auto_state = "wait_both"
        if not _spawn("both_zero"):
            _fail("both_zero_spawn_failed")
        return

    if _auto_state == "wait_both":
        _snapshot_batch("both_zero")
        if not _restore():
            _fail("both_zero_restore_failed")
            return
        assert _original_sig is not None
        if not _verify("manual_final", _original_sig):
            _fail("final_verify_failed")
            return
        _finish()


@hook(BALANCE_POST_BEGIN_PLAY, Type.POST)
def _balance_post_begin_play(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _batch_observed, _batch_target_hits

    # This exact lifecycle hook already worked in the earlier probes. Use it as the
    # readiness driver too, rather than guessing at a Tick UFunction.
    if _auto_state == "wait_player":
        _start_auto("InventoryBalanceStateComponent.PostBeginPlay")
        # The event which woke the state machine belongs to normal character/map load;
        # it must not contaminate our synthetic baseline.
        return

    if _auto_state not in ("wait_baseline", "wait_constant", "wait_both"):
        return
    if _active_batch == "<none>":
        return

    try:
        balance = obj.GetInventoryBalanceData()
    except Exception:
        return
    if not _is_a(balance, "CustomizationInventoryBalanceData"):
        return

    balance_path = _path(balance)
    try:
        name = str(obj.GetDisplayName())
    except Exception:
        name = balance_path

    _batch_observed += 1
    _batch_counts[name] += 1
    if balance_path == _target_balance_path:
        _batch_target_hits += 1

    if _batch_observed == _batch_requests:
        _advance_completed_batch()


def on_enable() -> None:
    global _auto_state, _auto_failed, _mutation_mode, _active_batch
    global _pool, _target_idx, _target_balance_path, _original_sig, _results

    _auto_state = "wait_player"
    _auto_failed = False
    _mutation_mode = "none"
    _active_batch = "<none>"
    _pool = None
    _target_idx = None
    _target_balance_path = ""
    _original_sig = None
    _results = {}

    logging.info(
        "[NDCAttributeAuto] ENABLED build=0.7.3 "
        "automation=armed; bootstrap=on_enable-or-balance-state-PostBeginPlay"
    )

    # Covers hot-enable/reload while already inside a fully loaded character.
    if _player_ready():
        _start_auto("on_enable")


def on_disable() -> None:
    global _auto_state
    if _mutation_mode != "none":
        logging.info("[NDCAttributeAuto] DISABLE restoring active mutation")
        _restore()
    _auto_state = "idle"


logging.info(
    "[NDCAttributeAuto] LOADED build=0.7.3 "
    "mode=event-driven-auto bootstrap=InventoryBalanceStateComponent.PostBeginPlay "
    f"requests_per_phase={REQUESTS}"
)

mod = build_mod(
    on_enable=on_enable,
    on_disable=on_disable,
)
