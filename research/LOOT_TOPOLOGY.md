# Loot topology research

Status: source-confirmed, runtime probe pending.

## Production invariant

NoDuplicateCosmetics must preserve both the semantics and the reachability of the original loot source. It must not blindly destroy an owned cosmetic after spawn, must not globally convert cosmetic rolls into weapon rolls, and must never introduce a cosmetic which the original source could not drop.

## Standard enemy world loot

`ItemPoolList_StandardEnemyGunsandGear` contains separate `FItemPoolInfo` entries. Each entry has its own `ItemPool`, `PoolProbability`, and `NumberOfTimesToSelectFromThisPool`.

Known base-game indices from existing BL3 loot research:

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

The cosmetic entry points to `ItemPool_SkinsAndMisc`. That pool is itself a weighted selector over six cosmetic sub-pools:

0. Heads
1. Skins
2. Weapon skins
3. Weapon trinkets
4. ECHO themes
5. Room decorations

For this topology the desired behavior is:

1. Preserve the original cosmetic `PoolProbability`.
2. When the cosmetic branch succeeds, consider only still-unlocked cosmetics which are actually reachable from that exact source through its vanilla child pools.
3. If the initially selected cosmetic is already owned, reroll only within that source-local reachable set; never substitute a cosmetic from another source or broader global pool.
4. If one cosmetic type is exhausted for this source, remove/zero only that exhausted child branch from this source's parent cosmetic selector so another still-eligible branch reachable from the same source can win naturally.
5. If all cosmetics reachable from that exact source are exhausted, suppress only that independent cosmetic branch: no cosmetic drops and no replacement weapon/gear roll.

## Other source topologies

Other sources must be classified before production mutation:

- Shared weighted pools containing gear and cosmetics: owned cosmetics should become ineligible and the existing weighted roll should resolve among remaining entries. This can naturally result in gear without adding an extra roll.
- Dedicated cosmetic pools: reroll only among still-unlocked cosmetics that belong to that exact drop pool. If that pool contains no eligible unowned cosmetic, it produces no replacement cosmetic.
- Nested/list-based sources: preserve the original reachability graph. Pool exhaustion may propagate upward only as far as required to prevent a successful parent roll from resolving to an empty child; it must not broaden eligibility to sibling/foreign pools which the source did not reference.

## Runtime probe

Development probe v0.2.0 adds:

- F5: dump standard enemy list and `ItemPool_SkinsAndMisc` topology.
- F6: spawn 20 rolls from the stock world cosmetic pool.
- F7-F12: targeted stock pool rolls for heads, skins, weapon skins, trinkets, ECHO themes, and room decorations.
- Per-pickup logging of balance, inventory data, resolved customization object, ownership result, and customization-part list.

The direct spawner is development-only and must not ship in the production mod.
