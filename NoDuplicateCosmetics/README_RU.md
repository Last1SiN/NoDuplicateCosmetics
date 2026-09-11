# NoDuplicateCosmetics 0.1.0 Candidate

Первый production-shaped candidate для Borderlands 3.

## Текущий scope

Эта версия фильтрует штатный world-cosmetic graph от `ItemPool_SkinsAndMisc`.
Пока она намеренно не заявляет поддержку всех mission/dedicated/container/DLC-specific
источников косметики.

## Поведение

- Уже открытая косметика становится недоступной до штатного weighted selection игры.
- Reroll остаётся только внутри loot graph, реально достижимого из исходного источника.
- Cosmetic roll никогда не превращается в дополнительный weapon roll.
- Штатный `Quantity`/no-drop исходного pool не меняется.
- Если child cosmetic pool полностью исчерпан, исключается только exact source-local
  ветка; exhaustion может подниматься выше только внутри этого же graph.
- Если исчерпан весь world-cosmetic root, cosmetic roll может закончиться no drop.
- Новая открытая в этой же сессии cosmetic подхватывается lazy ownership refresh без рестарта.

## Safety / compatibility

Candidate меняет только runtime `FAttributeInitializationData` shapes, которые уже были
проверены в игре:

- simple constant: `BaseValueConstant -> 0`;
- attribute-backed без DataTable/AttributeInitializer: одновременно
  `BaseValueConstant -> 0` и `BaseValueScale -> 0`, сохраняя attribute pointer.

Неизвестные weight shapes приводят к fail-closed. `Quantity`, `PoolProbability`, profile,
non-cosmetic entries и foreign pools не меняются.

Для каждого изменённого weight хранится точная исходная signature. Restore выполняется
только если live value всё ещё совпадает с filtered state, которым владеет мод; более
позднее изменение другим модом не перезаписывается.

## Установка

Скопировать `NoDuplicateCosmetics.sdkmod` без распаковки в `sdk_mods` и включить в Mod Menu.

## Статус тестирования

World pool topology, ownership, leaf exclusion, exhaustion propagation и attribute-backed
exclusion уже прошли bounded runtime probes. Этот пакет 0.1.0 — первая release-shaped
интеграция и требует обычного gameplay validation перед публичным релизом.
