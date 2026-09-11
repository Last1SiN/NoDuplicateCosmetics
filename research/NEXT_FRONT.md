# Next bounded front

The attribute-backed leaf exclusion boundary is now closed.

## Confirmed runtime contracts

1. Simple constant direct cosmetic leaves can be excluded by setting `Weight.BaseValueConstant = 0`.
2. Remaining positive sibling weights are renormalized by the native resolver rather than turning the removed leaf weight into a new no-drop slot.
3. Source-root `Quantity` must remain untouched so native no-drop behavior is preserved.
4. Dedicated cosmetic pools which have no eligible leaves produce no replacement cosmetic.
5. Exhausted source-local branches can be removed from a broader source so the broader native resolver chooses only among the source's remaining reachable branches.
6. Attribute-backed direct cosmetic leaves cannot be excluded by zeroing `BaseValueConstant` alone.
7. For the runtime-confirmed shape with positive `BaseValueConstant`, non-null `BaseValueAttribute`, null `AttributeInitializer`, no DataTable, and positive `BaseValueScale`, exclusion requires both `BaseValueConstant = 0` and `BaseValueScale = 0`, while preserving the attribute pointer and all other fields.
8. Exact guarded restore of mutated signatures has passed for both constant-only and attribute-backed cases.

## Current front: first production-shaped filter

Build a production-shaped source-local filter over the stock `ItemPool_SkinsAndMisc` graph, without the diagnostic spawner.

Required behavior:

- wait lazily until local profile/player ownership queries are authoritative;
- traverse only pools reachable from the exact stock world-cosmetic root;
- resolve direct cosmetic leaves through the three confirmed ownership APIs;
- classify each leaf weight by runtime shape;
- for owned simple-constant leaves, zero only `BaseValueConstant`;
- for owned attribute-backed leaves matching the proven contract, zero both `BaseValueConstant` and `BaseValueScale`;
- fail closed on DataTable-backed, AttributeInitializer-backed, unresolved, or otherwise unproven weight shapes;
- propagate child exhaustion upward only through source-local edges whose mutation semantics are proven;
- preserve `Quantity`, `PoolProbability`, non-cosmetic entries, and all foreign pools;
- keep exact captured signatures and restore only when the current live state still matches the mod-owned filtered state;
- refresh after ownership changes so a cosmetic learned during the same session becomes ineligible without restarting the game;
- no normal-operation info/debug spam in the release-shaped candidate.

## Still outside this front

- generic discovery of every mission/dedicated/container cosmetic source in the whole game;
- DataTable-backed and `AttributeInitializer`-backed weight mutation;
- multiplayer authority/client behavior;
- compatibility arbitration when another mod mutates the same exact weight after NoDuplicateCosmetics.

The purpose of the next build is to convert the proven world-graph mechanics into the first production-shaped implementation, then validate it with ordinary gameplay drops before broadening source coverage.
