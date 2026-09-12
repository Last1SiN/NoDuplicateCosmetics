# Next bounded front

The generic loaded-pool production candidate has passed its **initialization/reconcile** boundary.

Runtime evidence from `NoDuplicateCosmetics 0.2.0`:

- `loaded_pools=717`;
- `cosmetic_leaves=218`;
- `mapped_cosmetic=218`;
- `unmapped_cosmetic=0`;
- active profile `owned=1`;
- `filtered_leaves=1`;
- `exhausted_edges=0`;
- `unsupported_owned=0`;
- `ownership_unresolved=0`;
- `blocked=0`;
- `cycles=0`.

Evidence: `research/results/generic-loaded-pool-init-0.2.0.md`.

## Current bounded front: representative topology validation for 0.2.0

Do **not** claim generic all-source support from initialization alone.

Run a separate development-only validator alongside the production candidate. The validator may issue throttled stock `SpawnLootAsync` requests for observation, but it must not mutate loot weights, `Quantity`, `PoolProbability`, source selection counts, attachment probabilities, profile state, mission state, or production state.

Representative source-local roots:

1. **Dedicated mission cosmetic** — base-game mission weapon-trinket pool.
2. **Nested cosmetic** — slot-machine head pool.
3. **Mixed cosmetic/non-cosmetic** — red-chest flap pool.
4. **Stock world regression** — `ItemPool_SkinsAndMisc`.

For every case:

- rebuild the exact reachable graph;
- inspect current ownership and verify every owned reachable mapped cosmetic is already disabled by production before sampling;
- sample only from that exact root;
- require `owned_hits=0`;
- require no unresolved ownership results;
- require no observed balance outside that root's reachable graph;
- require unowned cosmetics to continue resolving when available;
- for the mixed chest root, require non-cosmetic results to continue resolving;
- for the world root, require native no-drop to remain present.

Coverage must be reported honestly: if a representative root contains no owned reachable cosmetic for the active profile, mark it as a control-only case instead of treating it as direct duplicate-exclusion proof.

## Boundary after representative topology validation

If the four-case validator passes with no semantic regressions, close the generalized loaded-pool selection boundary and move to lifecycle behavior:

1. same-session unlock refresh with a real newly learned cosmetic;
2. disable / guarded-restore gameplay validation;
3. multiplayer authority/client behavior;
4. compatibility arbitration when another mod changes a managed weight after filtering.
