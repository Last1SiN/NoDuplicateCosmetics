# NoDuplicateCosmetics

Borderlands 3 PythonSDK mod in development.

Goal: prevent already-unlocked cosmetics from being selected again while preserving the semantics of the original loot source.

## Current research contract

The mod must not blindly delete cosmetic pickups or globally convert cosmetic rolls into weapons.

For each source we first classify the loot topology:

- **Independent cosmetic roll** — if cosmetics are a separate `FItemPoolInfo` entry with their own `PoolProbability`, an owned cosmetic must be rerolled inside the same cosmetic pool. Weapon/gear probabilities stay untouched.
- **Shared weighted pool** — if cosmetic balances compete directly with weapon/gear balances inside one pool, an owned cosmetic is removed from the eligible weighted set and the original roll resolves among the remaining entries.
- **Dedicated cosmetic source** — reroll only among eligible unowned cosmetics from that source.

If a source has no eligible unowned cosmetics left, fallback behavior will be defined only after the source topology is verified in runtime; development must not silently invent extra weapon drops.

## Status

Source-first feasibility confirmed:

- `AOakPlayerController.IsCustomizationUnlocked(...)` exists for standard character customizations.
- `AOakPlayerController.IsInventoryCustomizationPartUnlocked(...)` exists for inventory customization parts such as weapon skins/trinkets.
- Standard enemy guns/gear lists contain cosmetics as a separate pool entry with their own probability rather than as a weapon-vs-cosmetic weighted choice.

Runtime probe work is being developed separately before production mutation logic is added.
