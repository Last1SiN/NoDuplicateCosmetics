# Next bounded front

The stock-world production behavior boundary is now closed.

`NoDuplicateCosmetics 0.1.2` plus the independent read-only validator confirmed:

- `20 pools / 139 leaves / 139 ownership mappings`;
- the active profile had `1` owned reachable world cosmetic and production filtered exactly `1` leaf;
- direct source-local sampling: `128/128`, `owned_hits=0`, `unresolved=0`, unowned siblings still resolved;
- world root sampling: `512` requests -> `235` cosmetic observations (`0.4590`), `owned_hits=0`, `unresolved=0`, `63` distinct cosmetics;
- all three ownership classes appeared;
- native world-root no-drop remained present;
- validator performed no mutation.

Evidence: `research/results/production-world-filter-validator-0.1.0.md`.

## Current bounded front: generic non-world source discovery

Do **not** broaden production mutation yet. First inventory and classify the exact source topologies which can award/drop cosmetics outside the already-covered stock world root.

Source-first class surfaces confirmed from generated headers:

1. **Mission rewards** — `UOakBaseMissionRewardData.ItemPoolReward` is a soft `UItemPoolData` reference.
2. **Dedicated enemy death loot** — `UAIBalanceStateComponent.DropOnDeathItemPools` and `CharacterExpansionDropOnDeathItemPools` are `FItemPoolCollection` sources; `FItemPoolCollection` contains direct `FItemPoolInfo` entries and `UItemPoolListData` references.
3. **Lootables / containers** — `ULootableComponent` is initialized from `ULootableBalanceData`; loot configurations contain `FLootAttachmentInfo`, whose `ItemPool` points to a `UItemPoolData`. Runtime `LootConfigurations` can also be inspected read-only.
4. **DLC/event source variants** — treat `/Game/PatchDLC/...` pools exactly like base-game pools, but preserve the original source owner and graph; do not fold them into a global cosmetic pool.

The first discovery implementation must be a separate development-only, read-only `.sdkmod` and must not mutate weights, `Quantity`, `PoolProbability`, mission/profile state, or production-mod state.

It should automatically, after player readiness:

- enumerate loaded `ItemPoolData` assets and classify every graph containing cosmetic leaves;
- enumerate loaded `OakBaseMissionRewardData` subclasses and record `ItemPoolReward` sources whose graph can reach cosmetics;
- enumerate loaded `AIBalanceStateComponent` objects and inspect both death-loot collections plus nested item-pool lists;
- enumerate loaded `LootableBalanceData`, `LootListData`, and runtime `LootableComponent` configurations and record item-pool attachments whose graph can reach cosmetics;
- classify each discovered root as `dedicated_cosmetic`, `mixed_cosmetic_noncosmetic`, or `nested_cosmetic`;
- record exact owner path, source field, root pool path, child-pool count, cosmetic/non-cosmetic leaf counts, unresolved entries, and package family (`/Game` vs `/Game/PatchDLC/...`);
- emit each unique source once and produce a compact summary;
- fail closed on unreadable/unresolved structures;
- never spawn loot and never change any live object.

Repeated scans are allowed only to discover newly-loaded map/DLC packages; avoid periodic duplicate spam.

## Boundary after discovery

Only after concrete source families/topologies are observed should production filtering be generalized. The generalized filter must operate on each exact source-local graph and preserve:

- original source reachability;
- source `PoolProbability` / selection count semantics;
- pool `Quantity` / no-drop semantics;
- non-cosmetic entries in mixed pools;
- exact guarded restore ownership.

Still separate later fronts:

- same-session unlock refresh with a real newly learned cosmetic;
- disable / guarded-restore gameplay validation;
- multiplayer authority/client behavior;
- compatibility arbitration when another mod changes a managed weight after filtering.
