# Same-session unlock validator 0.3.0 — contract correction

## Status

**INVALID AS PHYSICAL-PICKUP PROOF.**

The 0.3.0 run selected the unowned weapon trinket `Itsy Bitsy Rakky Hive` from the dedicated mission-28 pool and submitted one stock `SpawnLootAsync` request. The observer then saw an `InventoryBalanceStateComponent` for the expected balance and logged `TEST_ITEM_READY`.

That observation was insufficient. `InventoryBalanceStateComponent:PostBeginPlay` proves that the target inventory balance state was constructed, but it does **not** prove that a real, visible/pickable `ADroppedInventoryItemPickup` actor exists in the world.

The player reported that there was no visible pickup to collect. Therefore 0.3.0 must not be used as evidence for the same-session ownership transition boundary.

## Source confirmation

Generated game headers make the distinction explicit:

- `FSpawnDroppedPickupLootRequest` exposes `PickupSpawned` as `FSpawnDroppedPickupLootAsyncDelegate`;
- that delegate receives an `ADroppedInventoryItemPickup*`;
- `ADroppedInventoryItemPickup` derives from `AInventoryItemPickup`;
- `AInventoryItemPickup` exposes `GetInventoryBalanceStateComponent()`, `IsPickupInitialized()`, and `GiveInventoryToUser(...)`.

Thus a corrected validator can require the actual dropped pickup actor and verify its balance before allowing the ownership test to proceed.

## Corrected 0.3.1 contract

1. Snapshot the currently existing `DroppedInventoryItemPickup` actors before the test spawn.
2. Submit exactly one request from a one-item, currently-unowned dedicated cosmetic pool.
3. Poll for a **new** `DroppedInventoryItemPickup` actor.
4. Require that actor's `GetInventoryBalanceStateComponent().GetInventoryBalanceData()` to equal the selected target balance.
5. Log actor path, world location, distance to the player, and pickup initialization/active state.
6. Only after physical-actor confirmation, transfer that exact pickup into the player's inventory with `GiveInventoryToUser` so the player is not required to find a potentially misplaced world actor.
7. The validator still must not unlock the cosmetic or write profile ownership. The player uses/learns the item normally from inventory.
8. Detect the native ownership transition and verify production filters the exact target leaf in the same session.
9. Re-sample the same one-item dedicated pool and require zero target results.

Production `NoDuplicateCosmetics 0.2.0` is unchanged by this correction.
