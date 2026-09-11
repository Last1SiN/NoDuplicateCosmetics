# Pool exhaustion propagation — probe 0.6.0

Verdict: **BOUNDED REJECT FOR THIS TARGET; FAIL-CLOSED WORKED AS DESIGNED**.

Runtime log: `unrealsdk(20260911-142751).log`.

The planned synthetic target was the stock ECHO-theme pool. The probe intentionally required every touched leaf to use a simple positive constant `FAttributeInitializationData` before any mutation.

At runtime the first ECHO leaf immediately violated that assumption:

- balance: `/Game/PlayerCharacters/_Customizations/EchoDevice/ECHOTheme_07.InvBal_ECHOTheme_07`
- `BaseValueConstant = 1.0`
- `BaseValueAttribute = /Game/GameData/Loot/RarityWeighting/Att_RarityWeight_05_Legendary.Att_RarityWeight_05_Legendary`
- `BaseValueScale = 1.0`

Therefore probe 0.6.0 refused the plan before baseline spawning or mutation. Subsequent test-key presses correctly remained inert/refused because no mutation plan had been armed. No weights, Quantity, PoolProbability, or profile state were changed, and there were no captured records to restore.

## Consequence

ECHO themes cannot be used as the first constant-only exhaustion target. More importantly, this is direct runtime evidence that production cannot assume every cosmetic leaf has a constant-only weight. Attribute-backed leaf weights are a separate implementation boundary and must not be zeroed by changing only `BaseValueConstant` without first proving the resolver semantics of that `FAttributeInitializationData` form.

## Next experiment

Retain the exhaustion-propagation goal but switch to a bounded constant-only target. Use the stock character-head leaf pools, whose direct leaf weights are already runtime-proven for the Siren case and can be fail-closed validated for all four classes before mutation. Synthetic exhaustion will zero the 24 direct head leaves plus the exact simple world-root `ItemPool_SkinsAndMisc -> Heads` edge, while leaving the attribute-driven intermediate Heads->class selector untouched.

This allows us to establish:

1. direct dedicated-pool empty behavior on the Siren head pool;
2. category exhaustion propagation at the world root;
3. preservation of the root's native Quantity/no-drop behavior;
4. exact restore across a multi-entry exhaustion mutation.

Attribute-backed leaf filtering remains a later dedicated front.