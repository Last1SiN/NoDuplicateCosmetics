# Generic cosmetic-source discovery

Status: **active bounded front**. Production mutation remains limited to the already-validated stock world root.

## Source-first runtime surfaces

Generated-header evidence establishes the following source structures before any new mutation is attempted.

### Mission rewards

`UOakBaseMissionRewardData` exposes:

```cpp
TSoftObjectPtr<UItemPoolData> ItemPoolReward;
```

Therefore mission rewards can be discovered read-only by enumerating loaded subclasses of `OakBaseMissionRewardData`, resolving `ItemPoolReward`, and classifying the referenced pool graph.

### Dedicated enemy death loot

`UAIBalanceStateComponent` exposes:

```cpp
FItemPoolCollection DropOnDeathItemPools;
FItemPoolCollection CharacterExpansionDropOnDeathItemPools;
```

`FItemPoolCollection` contains both direct `FItemPoolInfo` records and nested `UItemPoolListData` references. `FItemPoolInfo` carries an `ItemPool`, `PoolProbability`, and `NumberOfTimesToSelectFromThisPool`.

This is the important semantic boundary for dedicated enemy drops: a cosmetic pool entry can coexist with gear pools as an independent collection entry. Any later production filter must preserve the enclosing collection's probability/selection-count semantics rather than creating replacement rolls.

### Lootables / containers

`ULootableComponent` is initialized from `ULootableBalanceData` and holds runtime `LootConfigurations`.

`ULootableBalanceData.DefaultLoot` and `ULootListData.LootData` are arrays of `FLootConfigurationInfo`. Each configuration contains `FLootAttachmentInfo` records, and each attachment points to an `ItemPoolData` plus its own attachment `Probability`.

Therefore container discovery must preserve the distinction between:

- the loot configuration weight;
- the attachment probability;
- the attached item-pool graph itself.

The source-discovery front is read-only and records these boundaries; it does not collapse them into a global cosmetic pool.

## Static public-source anchor

Public BL3 hotfix sources provide at least one concrete non-world dedicated cosmetic source example: Psychoreaver / `BPChar_PsychodinP2` is shown with a dedicated DLC4 room-decoration pool:

`/Game/PatchDLC/Alisma/GameData/Loot/Customization_Pool/ItemPool_Customizations_RoomDeco_Psychodin.ItemPool_Customizations_RoomDeco_Psychodin`

This is an anchor for runtime discovery, not a hardcoded production allowlist.

## Discovery output contract

The development-only source scanner must report each unique source as:

- source kind (`mission_reward`, `ai_death`, `lootable_balance`, `loot_list`, `lootable_runtime`, `pool_asset`);
- exact owner object path;
- exact source field / index path;
- exact root pool path;
- package family (`base` or first `/Game/PatchDLC/<name>` segment);
- topology classification (`dedicated_cosmetic`, `mixed_cosmetic_noncosmetic`, `nested_cosmetic`);
- reachable pool count;
- cosmetic leaf count;
- non-cosmetic leaf count;
- unresolved entry count.

It must never spawn loot or mutate weights, `Quantity`, `PoolProbability`, attachment probabilities, mission/profile state, or production-mod state.

Repeated scans may discover newly loaded maps/DLC packages, but duplicate sources must not be re-logged.
