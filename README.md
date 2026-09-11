# NoDuplicateCosmetics

Borderlands 3 PythonSDK mod in development.

Goal: prevent already-unlocked cosmetics from being selected again while preserving the semantics and reachability of the original loot source.

## Current research contract

The mod must not blindly delete cosmetic pickups or globally convert cosmetic rolls into weapons.

For each source we first classify the loot topology:

- **Independent cosmetic roll** — if cosmetics are a separate `FItemPoolInfo` entry with their own `PoolProbability`, an owned cosmetic may be rerolled only among still-unlocked cosmetics that are actually reachable from that exact source. If that source has no reachable unowned cosmetic left, its cosmetic roll produces no drop. Weapon/gear probabilities stay untouched.
- **Shared weighted pool** — if cosmetic balances compete directly with weapon/gear balances inside one pool, an owned cosmetic is removed from the eligible weighted set and the original roll resolves among the remaining entries. No extra roll is added.
- **Dedicated cosmetic source / pool** — reroll only among still-unlocked cosmetics belonging to that exact drop pool. Never broaden the candidate set to cosmetics which cannot normally drop from that pool.
- **Nested/list-based source** — preserve source reachability at every level. Pool exhaustion may propagate upward only far enough to prevent a successful parent branch from resolving into an empty child.

Core invariant: NoDuplicateCosmetics may reduce duplicate cosmetic output, but it must not make an item obtainable from a source which could not drop that item in vanilla.

## Status

Source-first feasibility confirmed:

- `AOakPlayerController.IsCustomizationUnlocked(...)` exists for standard character customizations.
- `AOakPlayerController.IsInventoryCustomizationPartUnlocked(...)` exists for inventory customization parts such as weapon skins/trinkets.
- Standard enemy guns/gear lists contain cosmetics as a separate pool entry with their own probability rather than as a weapon-vs-cosmetic weighted choice.

Runtime probe work is being developed separately before production mutation logic is added.
