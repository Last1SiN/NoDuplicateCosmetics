# Attribute-backed cosmetic weight probe 0.7.4

Status: PASS.

## Runtime result

The automatic 0.7.4 probe selected one direct stock ECHO-theme leaf with this live weight shape:

- `BaseValueConstant = 1.0`
- `BaseValueAttribute = /Game/GameData/Loot/RarityWeighting/Att_RarityWeight_03_Rare.Att_RarityWeight_03_Rare`
- `AttributeInitializer = None`
- `BaseValueScale = 1.0`

Three 128-request direct ECHO batches completed with `observed_ratio = 1.0` in every phase.

### Baseline

- requests: 128
- observed: 128
- target hits: 26

### Constant-only mutation

Mutation:

- `BaseValueConstant: 1.0 -> 0.0`
- preserve `BaseValueAttribute`
- preserve `BaseValueScale = 1.0`

Result:

- requests: 128
- observed: 128
- target hits: 25

Verdict: setting only `BaseValueConstant = 0` does **not** exclude an attribute-backed cosmetic leaf.

### Constant + scale zero mutation

Mutation:

- `BaseValueConstant: 1.0 -> 0.0`
- preserve `BaseValueAttribute`
- `BaseValueScale: 1.0 -> 0.0`

Result:

- requests: 128
- observed: 128
- target hits: 0
- other ECHO entries continued to resolve normally

Verdict: for the tested attribute-backed direct cosmetic leaf, zeroing both constant and scale makes that leaf ineligible while preserving reroll among sibling entries.

## Restore

Both mutation phases restored the exact captured weight signature successfully. Final verification matched the original signature.

## Production consequence

A generic owned-cosmetic filter cannot treat every `FAttributeInitializationData` as constant-only.

For direct cosmetic leaf entries with the runtime-confirmed shape:

- positive `BaseValueConstant`
- non-null `BaseValueAttribute`
- null `AttributeInitializer`
- no DataTable
- positive `BaseValueScale`

owned exclusion must zero both `BaseValueConstant` and `BaseValueScale`, while preserving the attribute pointer and all other fields. Restore must return both fields to their captured original values under an ownership guard.

This result applies only to the tested attribute-backed shape. DataTable-backed or AttributeInitializer-backed weights remain outside the proven mutation contract until separately classified.

## Safety note

Probe 0.7.3 was retired after a native access violation. It could call `SpawnLootAsync` from inside `InventoryBalanceStateComponent:PostBeginPlay`, creating unsafe re-entrant inventory construction. Probe 0.7.4 separated responsibilities: HUD frames drove mutations/spawns/state transitions and `PostBeginPlay` remained observation-only. The 0.7.4 run completed without a native crash.
