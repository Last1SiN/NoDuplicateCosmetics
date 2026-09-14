# NoDuplicateCosmetics 0.2.3

NoDuplicateCosmetics исключает уже открытые косметические предметы Borderlands 3 из поддерживаемых loot-графов, которые уже загружены игрой, **до native loot selection**, сохраняя исходную source-local структуру выбора.

## Проверенный scope

Этот релиз проверен для **single-player / local-player use**.

Поведение в co-op не валидировалось и не заявляется как поддерживаемое. Поэтому в package metadata сохраняется `coop_support = "Unknown"`.

## Поведение

- Уже открытые supported cosmetic leaves становятся ineligible до native selection.
- Прямые non-cosmetic entries не меняются.
- Новые entries не добавляются, pools не перенаправляются в посторонние pools.
- В mixed gear + cosmetic pools штатный resolver игры продолжает выбирать среди оставшихся source-local entries.
- Cosmetic-only child pool, который полностью исчерпан фильтрацией, может передать exhaustion только через свой точный parent edge.
- Unknown/unloaded branches остаются reachable.
- Unmapped cosmetics и неподдерживаемые weight shapes fail-open локально: их vanilla eligibility сохраняется вместо блокировки несвязанного loot.
- Newly loaded map/DLC pools подхватываются автоматически.
- Ownership обновляется в той же игровой сессии, поэтому новая изученная supported cosmetic становится ineligible без рестарта игры.

## Работа с weight

Изменяются только runtime-подтверждённые формы `FAttributeInitializationData`:

- simple constant weight: `BaseValueConstant -> 0`;
- supported attribute-backed weight: `BaseValueConstant -> 0` и `BaseValueScale -> 0`.

Мод не пишет pool `Quantity`, source `PoolProbability`, source selection counts, mission state, pickup state или profile ownership.

Для каждого managed weight сохраняются точные original и filtered signatures. Если другой мод меняет managed weight после фильтрации, NoDuplicateCosmetics оставляет внешнее значение нетронутым вместо того, чтобы перезаписать его при restore.

## Performance architecture в 0.2.3

В 0.2.3 удалён прежний периодический полный ownership/loot-graph reconcile. Граф строится один раз при смене local Pawn/HUD runtime context. Same-session ownership refresh запускается native RPC игры `ClientUnlockCustomization`, `ClientUnlockInventoryCustomizationPart` и `ClientUnlockCrewQuartersDecoration`, после чего выполняется один отложенный reconcile. В нормальной игре нет повторяющегося полного сканирования графа раз в одну или пять секунд.

## Late-loaded source coverage в 0.2.3

0.2.3 сохраняет no-polling архитектуру и добавляет source-aware event-driven rediscovery. Новые AI death-loot roots отслеживаются через инициализацию `AIBalanceStateComponent`, lootable/chest roots — через `LootableComponent.InitializeLootConfigurations`, mission rewards — через `Mission.CompleteMission`.

PRE hooks на native `SpawnLootAsync` и synchronous `SpawnLoot` служат last-chance guard: full rediscovery выполняется только если exact loaded source pool, который прямо сейчас должен резолвиться, ещё неизвестен production graph. Для `SpawnLootAsync` используется request boundary, потому что `FSpawnDroppedPickupLootRequest.ItemPools` содержит exact source-local pool list до native selection. Сам мод ни `SpawnLootAsync`, ни `SpawnLoot` не вызывает.

## Release validation

0.2.3 прошёл:

- representative dedicated, nested, mixed и world-drop topology tests;
- late-loaded `SpawnLootAsync` source recovery до native resolution;
- Graveward structural validation: все 139 reachable cosmetics owned и отфильтрованы, при этом normal/dedicated non-cosmetic loot остался reachable;
- real same-session cosmetic unlock refresh;
- disable -> exact restore -> re-enable/refilter;
- external weight-conflict arbitration и guarded restore;
- финальный production-only Graveward smoke: **15 kills, cosmetics 0, normal gear продолжал падать, dedicated loot продолжал падать, periodic stutter не наблюдался**. Тест завершился на 15 убийствах, потому что Commander перестал давать дальнейший respawn Graveward.

## Установка

Помести канонический файл `NoDuplicateCosmetics.sdkmod` напрямую в каталог Borderlands 3 `sdk_mods` и перезапусти игру. Не переименовывай `.sdkmod`: Oak требует, чтобы stem имени архива совпадал с именем единственной root folder внутри архива.

Если одновременно существует распакованная папка `sdk_mods/NoDuplicateCosmetics/`, удали или обнови её: extracted folder имеет приоритет над одноимённым `.sdkmod` и может незаметно запускать старую версию.

## Credits

Creator / implementation: Sol (ChatGPT, GPT-5.6 Sol)  
Testing, QA and maintenance: Last1SiN
