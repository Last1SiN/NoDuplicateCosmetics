# Next bounded front

The generalized loaded-pool selection boundary is closed for the representative topologies exercised by `NoDuplicateCosmeticsTopologyValidator 0.2.1`.

Evidence: `research/results/generic-topology-validator-0.2.1-pass.md`.

Confirmed runtime behavior with `NoDuplicateCosmetics 0.2.0`:

- dedicated mission cosmetic source remained source-local;
- nested slot-machine pool excluded the owned cosmetic and continued resolving unowned siblings;
- mixed red-chest pool excluded the owned cosmetic while continuing to resolve non-cosmetic loot;
- stock world root retained native no-drop;
- all sampled covered cases had `owned_hits=0`, `unresolved=0`, and `foreign=0`;
- production initialization remained clean at `717 loaded pools / 218 mapped cosmetic leaves`.

## Current bounded front: same-session real ownership refresh

Validate that production reacts correctly when a cosmetic changes from unowned to owned **without restarting the game**.

`NoDuplicateCosmeticsUnlockRefreshValidator 0.3.0` is retired as physical-pickup proof. Its `InventoryBalanceStateComponent:PostBeginPlay` observation showed only that the target balance state was constructed, not that a real `DroppedInventoryItemPickup` actor existed. See `research/results/same-session-unlock-refresh-validator-0.3.0-contract-correction.md`.

Use corrected validator 0.3.1. It must not write profile ownership or production-managed weights.

Required flow:

1. After player readiness, select a currently unowned cosmetic from a one-item dedicated cosmetic pool whose leaf has a supported weight shape.
2. Confirm the target is unowned and its leaf is still at the original eligible weight.
3. Snapshot existing `DroppedInventoryItemPickup` actors.
4. Submit one request from the exact target pool.
5. Require a **new real `DroppedInventoryItemPickup` actor** whose balance component resolves to the exact target balance.
6. Record actor path/location/distance and require pickup initialization before continuing.
7. Transfer that exact confirmed pickup into the player's inventory with `GiveInventoryToUser` so an off-screen/misplaced actor cannot block the test. This is test-harness inventory delivery only; it must not unlock the cosmetic or write profile ownership.
8. Wait for the player to use/learn the cosmetic normally. That native action is the real profile ownership transition.
9. Detect ownership `False -> True`, timestamp it, and verify production changes the target leaf to the proven disabled signature within the bounded refresh window.
10. After settling, issue a bounded set of requests from the same one-item dedicated pool and require zero target results.
11. Never mutate pool `Quantity`, source `PoolProbability`, source selection count, attachment probability, mission state, profile ownership, or any production-managed weight from the validator.

## Boundary after same-session refresh

If the real unlock transition passes, proceed to:

1. disable / guarded-restore gameplay validation;
2. multiplayer authority/client behavior;
3. compatibility arbitration when another mod changes a managed weight after filtering.
