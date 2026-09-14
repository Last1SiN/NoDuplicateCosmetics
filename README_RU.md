# NoDuplicateCosmetics

[English](README.md) | [Русский](README_RU.md)

NoDuplicateCosmetics — мод для Borderlands 3 PythonSDK, который не даёт уже открытым поддерживаемым косметическим предметам снова участвовать в выборе лута, сохраняя штатную source-local механику выпадений игры.

Вместо замены отклонённой косметики на посторонний лут мод делает уже открытые cosmetic entries недоступными **до native loot selection**, не меняя исходную структуру пулов, reachability, вероятности и количество выборов.

## Возможности

- Исключает уже открытые поддерживаемые cosmetics до native loot selection.
- Сохраняет штатный source-local loot graph и reachability каждого источника.
- Не заменяет заблокированную косметику оружием или другим несвязанным предметом.
- В mixed gear + cosmetic pools штатный resolver игры продолжает выбирать среди оставшихся eligible entries.
- Если dedicated cosmetic branch полностью исчерпан, из этой ветки просто не выпадает cosmetic.
- При исчерпании nested cosmetic-only pool отключается только точный parent edge, ведущий к этому child pool.
- Обновляет ownership после открытия косметики в той же игровой сессии.
- Подхватывает новые загруженные loot sources через event-driven hooks без периодического полного сканирования графа.
- Guarded restore не перезаписывает более позднее изменение weight, сделанное другим модом.
- Unsupported или unresolved cosmetic/weight shapes локально fail-open и не блокируют несвязанный лут.
- При обычной работе пишет в лог только ошибки.

## Требования

- Borderlands 3
- [BL3 PythonSDK / Oak Mod Manager](https://github.com/bl-sdk/oak-mod-manager/releases/latest)

Для установки и обновления SDK используйте [официальную инструкцию BL3 SDK / Oak](https://bl-sdk.github.io/oak-mod-db/).

## Установка мода

1. Установите или обновите BL3 PythonSDK / Oak по официальной инструкции выше.
2. Скачайте `NoDuplicateCosmetics.sdkmod` из [GitHub Releases](https://github.com/Last1SiN/NoDuplicateCosmetics/releases/latest).
3. При полностью закрытой Borderlands 3 скопируйте `.sdkmod` целиком в `Borderlands 3\sdk_mods\`. Сам `.sdkmod` не распаковывайте и не переименовывайте.
4. Если существует распакованная папка `sdk_mods/NoDuplicateCosmetics/`, удалите или обновите её: extracted folder имеет приоритет над одноимённым `.sdkmod`.
5. Запустите игру, откройте **MODS -> NoDuplicateCosmetics** и включите мод.

Для обновления NoDuplicateCosmetics замените существующий `.sdkmod` новым каноническим файлом и перезапустите игру.

## Совместимость и лицензия

- Проверенный scope: **single-player / local-player use**.
- Кооператив: **Unknown** — поведение в co-op пока не валидировалось.
- Мод не пишет pool `Quantity`, source `PoolProbability`, source selection counts, mission state, pickup state или profile ownership.
- Release 0.2.3 runtime-проверен на dedicated, nested, mixed и world-drop topology, late-loaded source recovery, same-session unlock refresh, disable/restore и third-party weight-conflict arbitration.
- Лицензия: **GNU GPLv3**.

## Credits

**Development:** Sol / GPT-5.6 Sol  
**Design, testing & QA:** Last1SiN

**BL3 PythonSDK / Oak Mod Manager:** создан [apple1417](https://github.com/apple1417) при участии проекта и контрибьюторов [BL-SDK](https://github.com/bl-sdk).
