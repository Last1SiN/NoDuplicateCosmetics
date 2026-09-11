# Loot topology research

Status: standard world topology and all six stock world-drop cosmetic ownership categories runtime-confirmed; native world-cosmetic no-drop semantics source-confirmed and runtime-observed. Generic source-local mutation design remains pending.

## Production invariant

NoDuplicateCosmetics must preserve both the semantics and the reachability of the original loot source. It must not blindly destroy an owned cosmetic after spawn, must not globally convert cosmetic rolls into weapon rolls, and must never introduce a cosmetic which the original source could not drop.

## Standard enemy world loot

`ItemPoolList_StandardEnemyGunsandGear` contains separate `FItemPoolInfo` entries. Each entry has its own `ItemPool`, `PoolProbability`, and `NumberOfTimesToSelectFromThisPool`.

Runtime-confirmed base-game indices:

- 0 health
- 1 needed ammo
- 2 emergency ammo
- 3 money
- 4 guns
- 5 class mods
- 6 shields
- 7 artifacts
- 8 grenade mods
- 9 cosmetics
- 10 eridium

Therefore the normal cosmetic world-drop roll is independent from the gun roll. Rejecting an already-owned cosmetic must not create an extra gun; doing so would increase the vanilla weapon drop rate.

The cosmetic entry points to `ItemPool_SkinsAndMisc`. Runtime confirms that this pool is a weighted selector over six cosmetic sub-pools, each with its own stock weight:

0. Heads
1. Skins
2. Weapon skins
3. Weapon trinkets
4. ECHO themes
5. Room decorations

The next layer is not uniform:

- Heads and skins each route through four character-specific child pools using character-weight attributes.
- Weapon skins directly contain balance entries.
- Weapon trinkets directly contain balance entries.
- ECHO themes directly contain balance entries.
- Room decorations route through rarity-specific child pools.

For this topology the desired behavior is:

1. Preserve the original cosmetic `PoolProbability`.
2. When the cosmetic branch succeeds, consider only still-unlocked cosmetics which are actually reachable from that exact source through its vanilla child pools.
3. If the initially selected cosmetic is already owned, reroll only within that source-local reachable set; never substitute a cosmetic from another source or broader global pool.
4. If one cosmetic type is exhausted for this source, remove/zero only that exhausted child branch from this source's parent cosmetic selector so another still-eligible branch reachable from the same source can win naturally.
5. If all cosmetics reachable from that exact source are exhausted, suppress only that independent cosmetic branch: no cosmetic drops and no replacement weapon/gear roll.
6. Preserve any native no-drop behavior inside the selected cosmetic pool; filtering must not turn a pool which can naturally resolve to no item into a guaranteed cosmetic drop.

## Ownership resolution

Runtime-confirmed ownership mappings:

- `OakCustomizationData` -> `AOakPlayerController.IsCustomizationUnlocked(...)`
- `OakInventoryCustomizationPartData` -> `AOakPlayerController.IsInventoryCustomizationPartUnlocked(...)`
- `CrewQuartersDecorationItemData` -> `AOakPlayerController.IsCrewQuartersDecorationUnlocked(...)`

Both `owned=NO` and `owned=YES` were observed for the primary customization path. A stock head (`Motosaurus`) resolved through `OakCustomizationData` and returned `owned=YES`, proving that the profile query can distinguish an already-unlocked world-drop cosmetic.

Category mapping is now runtime-confirmed across all six stock world-drop branches:

- Character heads -> `OakCustomizationData`
- Character skins -> `OakCustomizationData`
- ECHO themes -> `OakCustomizationData`
- Weapon skins -> `OakInventoryCustomizationPartData`
- Weapon trinkets -> `OakInventoryCustomizationPartData`
- Room decorations -> `CrewQuartersDecorationItemData`

Probe 0.3.2 confirmed room-decoration resolution with real world and direct room-decoration rolls; the earlier `owned=UNKNOWN` state from 0.3.0 is closed.

## Native no-drop behavior

Runtime repeatedly shows that direct requests against `ItemPool_SkinsAndMisc` do not guarantee one cosmetic per request. In the 0.3.2 run, 20 direct world-cosmetic requests produced 12 observed cosmetic balance states before the next batch.

Source evidence independently identifies the cause: the stock `ItemPool_SkinsAndMisc.Quantity` uses `/Game/GameData/Loot/ItemPools/Init_RandomLootCount_Normal`, which can evaluate below 1. Apocalyptech's Expanded Customization Pools explicitly replaces that `Quantity` with constant `1` to guarantee a cosmetic whenever the pool is rolled.

Therefore production filtering must leave the source pool's `Quantity` untouched. Owned-cosmetic filtering must operate on candidate eligibility/weights without converting a native no-drop result into a guaranteed item.

The 0.3.2 log did not contain a NumPad 1 topology/Quantity dump, so the exact live runtime initializer values from that run were not captured. This no longer blocks the semantic conclusion above, but the live dump may still be useful as an implementation sanity check.

## Other source topologies

Other sources must be classified before production mutation:

- Shared weighted pools containing gear and cosmetics: owned cosmetics should become ineligible and the existing weighted roll should resolve among remaining entries. This can naturally result in gear without adding an extra roll.
- Dedicated cosmetic pools: reroll only among still-unlocked cosmetics that belong to that exact drop pool. If that pool contains no eligible unowned cosmetic, it produces no replacement cosmetic.
- Nested/list-based sources: preserve the original reachability graph. Pool exhaustion may propagate upward only as far as required to prevent a successful parent roll from resolving to an empty child; it must not broaden eligibility to sibling/foreign pools which the source did not reference.

## Candidate mutation direction

The preferred next experiment is pre-selection eligibility mutation, not post-spawn deletion:

- retain every source's original graph, `Quantity`, `PoolProbability`, and non-cosmetic entries;
- mark only already-owned cosmetic leaf entries ineligible;
- propagate exhaustion upward only when a child branch can no longer produce any eligible result;
- never add entries or redirect to foreign pools;
- restore exact original weight data on disable;
- verify with direct stock-pool spawning before attempting generic all-source coverage.

The key unresolved implementation question is whether the game normalizes remaining `BalancedItems` weights after owned entries are made ineligible in the way required for source-local reroll semantics. That must be established with a bounded mutation probe before production implementation.

## Runtime probe

Probe 0.3.2 uses fixed, non-persistent NumPad bindings so saved F-key settings cannot override the diagnostic defaults:

- NumPad 0: scan loaded cosmetic balance states.
- NumPad 1: dump standard enemy topology and the seven tested cosmetic pools, including `Quantity`.
- NumPad 2: world cosmetics.
- NumPad 3: heads.
- NumPad 4: skins.
- NumPad 5: weapon skins.
- NumPad 6: weapon trinkets.
- NumPad 7: ECHO themes.
- NumPad 8: room decorations.

The direct spawner is development-only and must not ship in the production mod.
