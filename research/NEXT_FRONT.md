# Next bounded front

The generalized loaded-pool selection boundary is now closed for the representative topologies exercised by `NoDuplicateCosmeticsTopologyValidator 0.2.1`.

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

Use a separate development-only validator. It must not write profile ownership itself.

Preferred flow:

1. After player readiness, select a currently unowned cosmetic from a simple dedicated cosmetic pool whose leaf has a supported weight shape.
2. Confirm the target is currently unowned and its leaf is still eligible.
3. Spawn one pickup from that exact dedicated pool only to make the test item available; the validator itself must not consume/unlock it.
4. Wait for the player to pick up and use the cosmetic normally. This user action is the real profile ownership transition.
5. Detect the native ownership API transition `False -> True` and timestamp it.
6. Without restarting, verify production changes the exact target leaf to the already-proven disabled signature within the bounded refresh window.
7. After a quiet settle period, issue a bounded set of requests from the same single-item dedicated pool and require zero target results, proving same-session dedicated-pool exhaustion after the ownership transition.
8. Do not mutate `Quantity`, `PoolProbability`, source selection count, attachment probability, mission state, pickup ownership state, or any production-managed weight from the validator.
9. If no suitable unowned dedicated cosmetic exists, fail closed and report that no target was available.

The validator should choose from several already-observed one-item base-game mission cosmetic pools so it remains usable across different profile states.

## Boundary after same-session refresh

If the real unlock transition passes, proceed to:

1. disable / guarded-restore gameplay validation;
2. multiplayer authority/client behavior;
3. compatibility arbitration when another mod changes a managed weight after filtering.
