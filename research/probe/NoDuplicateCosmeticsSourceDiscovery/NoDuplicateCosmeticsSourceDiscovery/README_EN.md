# NoDuplicateCosmeticsSourceDiscovery 0.1.0

Development-only, read-only source scanner for Borderlands 3.

It automatically scans loaded mission rewards, AI death-loot collections, lootable/container definitions and runtime lootable configurations for item-pool graphs which can reach cosmetic balances. It also reports top-level loaded cosmetic-bearing item-pool candidates whose owning source is not yet resolved.

The scanner never spawns loot and never mutates weights, Quantity, PoolProbability, attachment probabilities, mission/profile state, or the production mod.

After a stable local player is present it scans every 10 seconds and logs each unique source once. Leave it enabled while moving between maps/DLCs to discover newly-loaded source packages. Send the resulting `unrealsdk.log` back for classification.
