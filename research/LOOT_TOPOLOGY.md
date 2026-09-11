# Loot topology research

Status: source-confirmed, runtime probe pending.

## Production invariant

NoDuplicateCosmetics must preserve the semantics of the loot source. It must not blindly destroy an owned cosmetic after spawn and must not globally convert cosmetic rolls into weapon rolls.

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
2. When the cosmetic branch succeeds, keep only unowned cosmetics eligible inside the relevant cosmetic pools.
3. If one cosmetic type is exhausted, remove/zero that type from the parent cosmetic selector so another still-eligible cosmetic type can win naturally.
4. If all cosmetic types reachable from that source are exhausted, suppress only that independent cosmetic branch. Do not manufacture an extra weapon/gear roll.

## Other source topologies

Other sources must be classified before production mutation:

- Shared weighted pools containing gear and cosmetics: owned cosmetics should become ineligible and the existing weighted roll should resolve among remaining entries. This can naturally result in gear without adding an extra roll.
- Dedicated cosmetic pools: reroll among unowned cosmetics reachable from that source.
- Nested/list-based sources: propagate pool exhaustion upward only as far as required to prevent a successful parent roll from resolving to an empty child.

## Runtime probe

Development probe v0.2.0 adds:

- F5: dump standard enemy list and `ItemPool_SkinsAndMisc` topology.
- F6: spawn 20 rolls from the stock world cosmetic pool.
- F7-F12: targeted stock pool rolls for heads, skins, weapon skins, trinkets, ECHO themes, and room decorations.
- Per-pickup logging of balance, inventory data, resolved customization object, ownership result, and customization-part list.

The direct spawner is development-only and must not ship in the production mod.
