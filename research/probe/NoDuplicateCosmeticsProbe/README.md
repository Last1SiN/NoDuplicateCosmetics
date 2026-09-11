# NoDuplicateCosmeticsProbe 0.3.1

Development-only probe for NoDuplicateCosmetics.

It does not modify loot weights, loot pools, profile data, or unlocked cosmetics. It can deliberately spawn loot from stock cosmetic pools for fast testing.

## Keybinds

- NumPad 0: scan all currently loaded inventory balance states and log cosmetic states
- NumPad 1: dump standard enemy topology plus the world cosmetic selector and all six stock leaf cosmetic pools, including each pool's Quantity initializer
- NumPad 2: spawn 20 rolls from the stock world cosmetic pool (`ItemPool_SkinsAndMisc`)
- NumPad 3: spawn 10 head-pool rolls
- NumPad 4: spawn 10 skin-pool rolls
- NumPad 5: spawn 10 weapon-skin-pool rolls
- NumPad 6: spawn 10 weapon-trinket-pool rolls
- NumPad 7: spawn 10 ECHO-theme-pool rolls
- NumPad 8: spawn 10 room-decoration-pool rolls
- NumPad 9: unused

Probe 0.3.1 observes cosmetic balance states through `InventoryBalanceStateComponent:PostBeginPlay` and supports a manual NumPad 0 scan.

Ownership resolution covers:

- `OakCustomizationData` through `IsCustomizationUnlocked`
- `OakInventoryCustomizationPartData` through `IsInventoryCustomizationPartUnlocked`
- `CrewQuartersDecorationItemData` through `IsCrewQuartersDecorationUnlocked`

The direct spawner exists only to accelerate development. It is not planned for the production mod.
