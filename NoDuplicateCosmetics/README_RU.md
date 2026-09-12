# NoDuplicateCosmetics 0.2.0 Candidate

Generic loaded-pool production candidate для Borderlands 3.

## Текущий scope

0.2.0 расширяет уже проверенный stock-world filter. Вместо одного жёстко заданного
`ItemPool_SkinsAndMisc` мод периодически обнаруживает все currently loaded
`ItemPoolData` и фильтрует supported owned cosmetic leaves прямо в их существующих
графах.

Это всё ещё validation candidate, а не заявление о готовом all-source релизе.

## Поведение

- Уже открытые supported cosmetics становятся ineligible до native selection.
- Прямые non-cosmetic entries не меняются.
- Новые entries не добавляются, pools никуда не перенаправляются.
- Child exhaustion поднимается вверх только если child cosmetic-only, больше ничего
  не может выдать и был исчерпан хотя бы частично фильтрацией этого мода.
- Unknown/unloaded child graphs остаются reachable.
- Unmapped cosmetics и неподдерживаемые weight shapes fail-open локально: vanilla
  eligibility сохраняется, остальные pools продолжают фильтроваться.
- Newly loaded map/DLC pools автоматически подхватываются.
- Ownership повторно проверяется раз в секунду, поэтому новая изученная mapped cosmetic
  может стать ineligible без рестарта игры.

## Weight transforms

Меняются только две уже подтверждённые runtime формы `FAttributeInitializationData`:

- simple constant: `BaseValueConstant -> 0`;
- attribute-backed без DataTable/AttributeInitializer:
  `BaseValueConstant -> 0` и `BaseValueScale -> 0`.

`BaseValueAttribute` и остальные поля сохраняются.

## Safety / compatibility

Мод не пишет pool `Quantity`, source `PoolProbability`, source selection count,
loot-attachment probability, mission state, pickup state или profile ownership.

Для каждого managed weight сохраняются точные original и filtered signatures.
Restore выполняется только пока live value совпадает с filtered state этого мода.
Если другой мод позже изменил weight, его значение не перезаписывается, а entry
блокируется от дальнейшего управления на эту сессию.

## Статус

Stock-world selection semantics уже независимо прошли PASS. Для 0.2.0 теперь нужна
runtime-проверка representative источников:

- dedicated mission cosmetic pool;
- nested slot-machine cosmetic pool;
- mixed chest pool;
- stock-world pool как regression control.

Co-op support пока Unknown.
