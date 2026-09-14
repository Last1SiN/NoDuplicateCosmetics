# NoDuplicateCosmetics

[English](README.md) | [Русский](README_RU.md)

NoDuplicateCosmetics — мод для Borderlands 3 PythonSDK, который не даёт уже открытым косметическим предметам снова участвовать в выборе лута, сохраняя штатную source-local механику выпадений игры.

Вместо замены отклонённой косметики на посторонний лут мод делает уже открытые cosmetic entries недоступными **до native loot selection**, не меняя исходную структуру пулов, reachability, вероятности и количество выборов.

## Возможности

- Исключает уже открытые косметические предметы до выбора лута при выпадении.
- Сохраняет штатный source-local loot graph и reachability каждого источника.
- В mixed gear + cosmetic pools штатный resolver игры продолжает выбирать лут.
- Если dedicated cosmetic branch полностью исчерпан, из этой ветки просто не выпадает cosmetic.

## Требования

- Borderlands 3
- [BL3 PythonSDK / Oak Mod Manager](https://github.com/bl-sdk/oak-mod-manager/releases/latest)

Для установки и обновления SDK используйте [официальную инструкцию BL3 SDK / Oak](https://bl-sdk.github.io/oak-mod-db/).

## Установка мода

1. Установите или обновите BL3 PythonSDK / Oak по официальной инструкции выше.
2. Скачайте `NoDuplicateCosmetics.sdkmod` из [GitHub Releases](https://github.com/Last1SiN/NoDuplicateCosmetics/releases/latest).
3. При полностью закрытой Borderlands 3 скопируйте `.sdkmod` целиком в `Borderlands 3\sdk_mods\`. Сам `.sdkmod` распаковывать не нужно.
4. Удалите старые test/probe-сборки NoDuplicateCosmetics, чтобы одновременно загружалась только одна runtime-версия NoDuplicateCosmetics.
5. Запустите игру, откройте **MODS -> NoDuplicateCosmetics** и включите мод.

Для обновления замените существующий `.sdkmod` новым файлом и перезапустите игру.

## Совместимость и лицензия

- Мод не заменяет отфильтрованную косметику посторонним лутом.
- Структура пулов, source-local reachability, вероятности и количество выборов остаются штатными.
- Кооператив: **Unknown** — поведение в co-op пока не валидировалось.
- Лицензия: **GNU GPLv3 с [дополнительными условиями Section 7 о происхождении разработки](ADDITIONAL_TERMS.md)**

## Credits

**Development:** Sol / GPT-5.6 Sol  
**Design, testing & QA:** Last1SiN

**BL3 PythonSDK / Oak Mod Manager:** создан [apple1417](https://github.com/apple1417) при участии проекта и контрибьюторов [BL-SDK](https://github.com/bl-sdk).
