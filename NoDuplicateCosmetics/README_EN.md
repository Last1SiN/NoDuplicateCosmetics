# NoDuplicateCosmetics 0.2.3

NoDuplicateCosmetics filters already-owned Borderlands 3 cosmetics out of the loot
graphs which are currently loaded by the game, while preserving the source-local
selection structure.

## Validated scope

This release is validated for **single-player / local-player use**.

Co-op behavior has not been validated and is not claimed as supported. The package keeps
`coop_support = "Unknown"` for that reason.

## Behavior

- Already-owned supported cosmetic leaves become ineligible before native selection.
- Direct non-cosmetic entries are never changed.
- No entries are added and no pool is redirected to an unrelated pool.
- Mixed gear + cosmetic pools continue using the game's native resolver among the
  remaining source-local entries.
- A cosmetic-only child pool which becomes exhausted can propagate that exhaustion only
  through its exact parent edge.
- Unknown/unloaded graph branches remain reachable.
- Unmapped cosmetics and unsupported weight shapes fail open locally: their vanilla
  eligibility is left untouched rather than rejecting unrelated loot.
- Newly loaded map/DLC pools are discovered automatically.
- Ownership is refreshed during play, so a newly learned supported cosmetic can become
  ineligible without restarting the game.

## Runtime-validated cases

The implementation has been exercised against:

- dedicated cosmetic pools;
- nested cosmetic pools;
- mixed cosmetic/non-cosmetic pools;
- the stock world cosmetic root with native no-drop preserved;
- a real same-session cosmetic unlock;
- disable -> restore -> re-enable lifecycle;
- an external third-party weight conflict, including guarded restore and later
  re-baselining.

## Weight handling

Only runtime-proven `FAttributeInitializationData` forms are modified:

- simple constant weight: `BaseValueConstant -> 0`;
- supported attribute-backed weight:
  `BaseValueConstant -> 0` and `BaseValueScale -> 0`.

The mod does not write pool `Quantity`, source `PoolProbability`, source selection
counts, mission state, pickup state, or profile ownership.

Each managed weight stores exact original and filtered signatures. If another mod changes
a managed weight after filtering, NoDuplicateCosmetics leaves that external value
untouched instead of restoring over it.

## Installation

Place the canonical `NoDuplicateCosmetics.sdkmod` file directly in the Borderlands 3
`sdk_mods` directory and restart the game. Do not rename the archive: Oak requires the
`.sdkmod` filename stem to match its single root folder name. If an extracted
`sdk_mods/NoDuplicateCosmetics/` folder also exists, remove or update it because an
extracted folder shadows the same-named `.sdkmod`.

## Credits

Creator / implementation: Sol (ChatGPT, GPT-5.6 Sol)  
Testing, QA and maintenance: Last1SiN

## Performance architecture in 0.2.3

0.2.3 removes the previous periodic full ownership/loot-graph reconciliation. The graph is rebuilt once when the local Pawn/HUD runtime context changes. Same-session ownership refresh is triggered by the game's native `ClientUnlockCustomization`, `ClientUnlockInventoryCustomizationPart`, and `ClientUnlockCrewQuartersDecoration` RPCs, followed by one delayed reconcile. There is no recurring one-second or five-second full graph scan during normal play.

## Late-loaded source coverage in 0.2.3

0.2.3 keeps the no-polling performance architecture and adds source-aware, event-driven rediscovery. New AI death-loot roots are detected from `AIBalanceStateComponent` game-stage initialization, lootable/chest roots from `LootableComponent.InitializeLootConfigurations`, and mission rewards at `Mission.CompleteMission`. PRE hooks on native `SpawnLootAsync` and synchronous `SpawnLoot` are last-chance guards: they only rebuild the graph when the exact loaded source pool about to be resolved is not already known. `SpawnLootAsync` is covered at its request boundary because `FSpawnDroppedPickupLootRequest.ItemPools` carries the exact source-local pool list before native selection. The mod never calls either loot-spawn function itself.

Normal gameplay still has no recurring one-second/five-second full scan. Full rediscovery occurs only when a genuinely new loaded loot pool is observed.

## Release validation

Release 0.2.3 passed the late-loaded `SpawnLootAsync` boundary test, Graveward structural validation, real same-session unlock refresh, disable/restore/re-enable, and external-conflict arbitration. The final production-only gameplay smoke completed 15 repeated Graveward kills before the Commander respawn loop stopped producing further respawns: 0 cosmetics observed, normal gear continued, dedicated Graveward loot continued, and no periodic stutter was observed.
