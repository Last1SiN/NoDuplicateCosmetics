# NoDuplicateCosmeticsProbe 0.3.0

Development-only probe for NoDuplicateCosmetics.

It does not modify loot weights, loot pools, profile data, or unlocked cosmetics. It can deliberately spawn loot from stock cosmetic pools for fast testing.

## Keybinds

- F4: scan all currently loaded inventory balance states and log cosmetic states
- F5: dump standard enemy topology plus the world cosmetic selector and all six stock leaf cosmetic pools
- F6: spawn 20 rolls from the stock world cosmetic pool (`ItemPool_SkinsAndMisc`)
- F7: spawn 10 head-pool rolls
- F8: spawn 10 skin-pool rolls
- F9: spawn 10 weapon-skin-pool rolls
- F10: spawn 10 weapon-trinket-pool rolls
- F11: spawn 10 ECHO-theme-pool rolls
- F12: spawn 10 room-decoration-pool rolls

Probe 0.3.0 observes cosmetic balance states through `InventoryBalanceStateComponent:PostBeginPlay` and also supports the manual F4 scan. This replaces the unreliable pickup-activation-only observation path used by 0.2.0.

The direct spawner exists only to accelerate development. It is not planned for the production mod.
