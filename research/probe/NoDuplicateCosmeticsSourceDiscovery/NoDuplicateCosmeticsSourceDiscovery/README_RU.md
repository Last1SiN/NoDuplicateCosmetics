# NoDuplicateCosmeticsSourceDiscovery 0.1.0

Development-only read-only scanner источников косметического loot для Borderlands 3.

Он автоматически проверяет загруженные mission rewards, AI death-loot collections, lootable/container definitions и runtime lootable configurations на item-pool graphs, которые могут привести к cosmetic balances. Дополнительно пишет top-level loaded cosmetic-bearing item-pool candidates, для которых owner пока не разрешён.

Scanner ничего не спавнит и не меняет weights, Quantity, PoolProbability, attachment probabilities, mission/profile state или production-мод.

После появления стабильного local player он делает scan раз в 10 секунд и пишет каждый уникальный source только один раз. Можно оставить его включённым при переходах по картам/DLC, чтобы захватывать newly-loaded source packages. После прогона пришли `unrealsdk.log`.
