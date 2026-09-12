# Generic source discovery 0.1.0 runtime result

Verdict: **PASS for the bounded discovery front; enough real source surfaces are confirmed to start a generic loaded-pool production candidate.**

Observed runtime facts from `unrealsdk(20260912-081037).log` with `NoDuplicateCosmetics 0.1.2` and the read-only `NoDuplicateCosmeticsSourceDiscovery 0.1.0` enabled:

- production 0.1.2 still initialized cleanly at **20 stock-world pools / 139 cosmetic leaves**, with **1 owned leaf filtered**, `exhausted_edges=0`, `blocked=0`;
- discovery scan 1 found **40 concrete source bindings** plus **58 top-level cosmetic-bearing pool candidates** with **0 scanner errors**;
- scan 2 added one runtime AI source, giving **41 concrete source bindings** total and still **0 errors**;
- concrete source bindings were: **15 mission reward**, **9 AI death-loot**, **11 lootable-balance**, and **6 runtime lootable** bindings;
- mission reward examples resolve through `ItemPoolReward` and are dedicated one-leaf cosmetic pools in the observed set, including base-game weapon-trinket rewards and Alisma mission rewards;
- standard enemy `AIBalanceStateComponent.DropOnDeathItemPools.ItemPoolLists[0].ItemPools[9]` resolves to the already-validated nested `ItemPool_SkinsAndMisc` graph;
- Eridian red-chest attachment sources resolve to mixed cosmetic/non-cosmetic graphs (`ItemPool_RedChestFlaps` and `ItemPool_ChestFlaps`), demonstrating a real mixed topology outside the stock-world root;
- slot-machine loot definitions resolve to nested cosmetic-only graphs for room decorations, player skins, player heads, weapon trinkets, and weapon skins;
- loaded top-level candidates additionally expose base-game crew-challenge pools plus DLC/event cosmetic pools from Alisma, BloodyHarvest, Dandelion, Event2, EventVDay, Geranium, and Hibiscus;
- all emitted source/candidate graph analyses in this run reported `unresolved=0`.

## Architectural consequence

The production engine no longer needs to be rooted specifically at `ItemPool_SkinsAndMisc`.

A generic loaded-pool filter can preserve source-local semantics by operating only on each live `ItemPoolData.BalancedItems` graph:

1. classify each direct leaf as cosmetic or non-cosmetic;
2. query ownership only for cosmetic leaves;
3. make a supported owned cosmetic leaf ineligible using the already-proven weight transforms;
4. leave non-cosmetic leaves untouched and available;
5. recursively treat a child as exhausted only when that child graph has no remaining available result;
6. propagate exhaustion by disabling only the exact parent `BalancedItems` edge, and only when that edge has a proven supported weight shape;
7. never add entries or redirect to any foreign pool;
8. never write `Quantity`, `PoolProbability`, attachment probability, mission state, or profile state;
9. unknown ownership/weight shapes fail open for that leaf/edge (leave vanilla eligibility untouched), preventing accidental broad source suppression;
10. retain exact guarded restore ownership per mutated `BalancedItems` entry.

This same algorithm covers dedicated cosmetic pools, mixed gear+cosmetic pools, and nested cosmetic graphs without source-specific reroll code because the stock resolver performs the reroll inside the original graph after ineligible entries are zeroed.

## Next bounded front

Build `NoDuplicateCosmetics 0.2.0` as a generic **loaded ItemPoolData** production candidate:

- periodically discover newly loaded item pools rather than hard-coding source paths;
- build one deduplicated graph across loaded pools;
- map every loaded cosmetic balance for which one of the three proven ownership APIs is available;
- filter only supported owned cosmetic leaves;
- keep unsupported/unmapped leaves available and report them once instead of rejecting the entire graph;
- propagate exact child exhaustion through supported parent edges only;
- preserve the 0.1.2 guarded compatibility/restore rules;
- keep normal operation quiet except one startup/refresh diagnostic summary and errors.

Validation must first be read-only/observational against representative dedicated, mixed, and nested source pools before any release claim of all-source coverage.
