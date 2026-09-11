# Attribute-backed leaf exclusion — probe 0.7.0

Verdict: **PARTIAL PASS; constant-only is disproven, constant+scale zero is the current viable candidate.**

Runtime log: `unrealsdk(20260911-154549).log`.

## Runtime target

The probe selected stock ECHO leaf index 0:

- balance: `/Game/PlayerCharacters/_Customizations/EchoDevice/ECHOTheme_07.InvBal_ECHOTheme_07`
- `BaseValueConstant = 1.0`
- `BaseValueAttribute = /Game/GameData/Loot/RarityWeighting/Att_RarityWeight_05_Legendary.Att_RarityWeight_05_Legendary`
- `BaseValueScale = 1.0`

All 12 direct ECHO leaves matched the bounded attribute-backed form used by the experiment.

## Baseline

512 direct ECHO requests:

- observed: 512
- target hits: 3
- distinct results: 11

## Constant-only phase

Only `BaseValueConstant` was changed from `1.0` to `0.0`; the rarity `BaseValueAttribute` and `BaseValueScale=1.0` were left intact.

512 requests:

- observed: 512
- target hits: 2
- distinct results: 12

Therefore **`BaseValueConstant=0` does not make this attribute-backed entry ineligible**. This mutation form is rejected for production filtering of this weight shape.

Exact captured signature was then restored successfully.

## Constant + scale zero phase

The same target was changed to:

- `BaseValueConstant = 0.0`
- original `BaseValueAttribute` preserved
- `BaseValueScale = 0.0`

512 requests:

- observed: 512
- target hits: 0
- distinct results: 10

The remaining ECHO entries continued to resolve normally, and the exact captured signature was restored successfully afterward. Final manual verification also matched the original signature.

## Consequence

For the tested attribute-backed ECHO leaf:

1. zeroing only `BaseValueConstant` is **not** a valid exclusion mechanism;
2. zeroing both `BaseValueConstant` and `BaseValueScale` is the current viable exclusion candidate;
3. the 0/512 result is directionally strong but the selected target was Legendary-weighted and only appeared 3/512 at baseline, so a stronger high-frequency runtime confirmation is still appropriate before treating the mutation form as production-proven.

## Next bounded front

Automate the same experiment after player load and select a runtime-discovered Common attribute-backed ECHO leaf when available. This raises target sample frequency while reducing manual test work. Probe 0.7.1 implements that automatic sequence and emits a final `AUTO_VERDICT` line.
