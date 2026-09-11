# Attribute-weight auto-probe safety follow-up

## 0.7.1 — HUNG / NO DRIVER EVENTS

`unrealsdk(20260911-155758).log` showed the probe loading and arming, but no readiness event or phase transition followed. The guessed `Engine.GameViewportClient:Tick` driver was therefore not usable in the tested BL3 runtime.

## 0.7.2 — HUNG / NO DRIVER EVENTS

`unrealsdk(20260911-160421).log` again showed only `LOADED` and `ENABLED`; no `PLAYER_DETECTED` or `PLAYER_READY` event arrived from `/Script/OakGame.OakPlayerController:PlayerTick`. That driver is also rejected for this runtime.

## 0.7.3 — NATIVE CRASH / RETIRED

The event-driven rewrite started work from `InventoryBalanceStateComponent:PostBeginPlay`. That design allowed `SpawnLootAsync` and later phase transitions to originate from inside an inventory-balance construction callback. Testing produced a native BL3 `EXCEPTION_ACCESS_VIOLATION` (`0xffffffffffffffff`). The stack was unsymbolized, so exact native causality is not proven, but re-entering inventory construction from its own lifecycle callback is an unsafe design and is retired regardless.

Do not use probe 0.7.3 again.

## 0.7.4 — SAFETY REWRITE

0.7.4 separates control and observation:

- `/Script/Engine.HUD:ReceiveDrawHUD` is the only driver for readiness, mutation, spawning, restore, timeout handling, and phase transitions.
- `InventoryBalanceStateComponent:PostBeginPlay` is observation-only.
- No spawn, mutation, restore, or state transition is allowed from the construction callback.
- Synthetic spawning is throttled to 8 requests per HUD frame.
- Each phase is reduced from 256 to 128 direct ECHO requests; the target prefers a Common attribute-backed leaf for high sample frequency.
- All pool mutations retain guarded exact restore.

This keeps every Unreal mutation on an ordinary game-thread HUD frame and avoids construction-hook re-entrancy.
