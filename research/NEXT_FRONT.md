# Next bounded front

The generic non-world source discovery boundary is now closed sufficiently to start a production-shaped generalized filter.

Runtime evidence from `NoDuplicateCosmeticsSourceDiscovery 0.1.0`:

- **41 concrete cosmetic-bearing source bindings** were observed with **0 scanner errors**;
- source classes included **15 mission reward**, **9 AI death-loot**, **11 lootable-balance**, and **6 runtime lootable** bindings;
- **58 top-level cosmetic-bearing pool candidates** were classified with no unresolved graph entries;
- real observed topologies include dedicated cosmetic mission pools, nested cosmetic slot-machine pools, the already-known nested stock-world root, and mixed cosmetic/non-cosmetic chest pools;
- loaded candidates additionally cover base-game crew-challenge content and multiple `/Game/PatchDLC/...` families.

Evidence: `research/results/generic-source-discovery-0.1.0.md`.

## Current bounded front: generic loaded-pool production filter 0.2.0

Generalize the proven 0.1.2 filter from one hard-coded root to the set of **currently loaded `ItemPoolData` graphs**.

The production candidate must remain graph-preserving and source-local:

1. Discover loaded item pools periodically so newly loaded map/DLC content can join without hard-coded paths.
2. Build one deduplicated directed graph keyed by live pool path.
3. Distinguish direct cosmetic leaves, direct non-cosmetic leaves, and child-pool edges.
4. Query ownership only for cosmetic leaves using the three proven APIs.
5. For a supported owned cosmetic leaf, apply the already-proven weight transform:
   - simple constant -> `BaseValueConstant = 0`;
   - attribute-backed/no-table/no-initializer -> `BaseValueConstant = 0` and `BaseValueScale = 0`.
6. Leave non-cosmetic leaves untouched and eligible.
7. Unsupported/unmapped cosmetic leaves fail open locally: leave their vanilla weight untouched and keep that branch reachable; do not reject or restore unrelated graphs.
8. Recursively propagate a child as exhausted only when its graph has no remaining available result; disable only the exact parent `BalancedItems` edge and only when that edge has a supported weight shape.
9. Never add entries, redirect to foreign pools, or broaden source reachability.
10. Never write pool `Quantity`, source `PoolProbability`, source selection count, attachment probability, mission state, profile state, or pickup state.
11. Preserve exact guarded ownership/restore per managed `BalancedItems` entry. If another mod changes a managed weight after filtering, stop managing that entry rather than overwriting the external value.
12. Keep normal operation quiet except a bounded READY/refresh summary and errors.

## Validation boundary for 0.2.0

Do not claim generic all-source support merely because the generalized candidate initializes.

Use a separate read-only validator to inspect representative source-local graphs already proven to exist:

- one dedicated mission cosmetic pool;
- one nested slot-machine cosmetic pool;
- one mixed chest pool;
- the stock-world graph as a regression control.

For each representative pool, verify that owned reachable cosmetics are ineligible, unowned/non-cosmetic siblings remain eligible, no foreign content is introduced, and native no-drop/selection semantics remain intact.

Still separate later fronts:

- same-session unlock refresh with a real newly learned cosmetic;
- disable / guarded-restore gameplay validation;
- multiplayer authority/client behavior;
- compatibility arbitration when another mod changes a managed weight after filtering.
