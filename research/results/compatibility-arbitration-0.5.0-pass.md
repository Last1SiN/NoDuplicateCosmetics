# Compatibility arbitration 0.5.0 — PASS

Production candidate: `NoDuplicateCosmetics 0.2.0`
Validator: `NoDuplicateCosmeticsCompatibilityValidator 0.5.0`

## Verdict

**PASS** for the exercised owned one-item mission trinket leaf under deliberate third-party-style weight mutation.

## Runtime evidence

Target:

`/Game/Gear/WeaponTrinkets/_Design/TrinketParts/WeaponTrinket_28.InvBal_WeaponTrinket_28`

Observed sequence:

- production initialized cleanly with `717` loaded pools, `218` mapped cosmetic leaves, `owned=2`, `filtered_leaves=2`, and zero unsupported/unresolved/blocked/cycle counts;
- baseline disable restored the target's original constant weight after `93.7 ms`;
- production was re-enabled and re-filtered the target;
- validator injected a synthetic positive external value (`BaseValueConstant=0.5`, scale unchanged at `1.0`) after production had filtered the leaf;
- production detected that the managed weight had changed externally and logged that filtering was disabled for that exact managed key;
- the external value remained untouched for more than one production refresh interval (`2007.2 ms`), proving production did not overwrite the third-party value while enabled;
- production disable preserved that external value (`GUARDED_RESTORE_PASS`, `8.4 ms`), proving guarded restore did not overwrite it with the old captured vanilla value;
- after re-enable, production accepted the external value as the new baseline and filtered from it (`EXTERNAL_BASELINE_REFILTER_PASS`, `2222.8 ms`);
- the next disable restored that same external baseline (`EXTERNAL_BASELINE_RESTORE_PASS`, `7.9 ms`);
- validator cleanup restored the captured vanilla baseline, re-enabled production, and production returned to the normal filtered state (`cleanup_refilter_ms=2232.8`);
- final state: production enabled and vanilla baseline restored beneath the production filter.

Final validator line reported:

`AUTO_VERDICT PASS ... external_value_preserved_during_conflict=YES production_left_enabled=YES vanilla_baseline_restored=YES`

## Conclusion

For the exercised supported constant-weight leaf, `NoDuplicateCosmetics 0.2.0` behaves as a cooperative overlay:

1. it does not continuously overwrite a later external weight change;
2. its guarded restore leaves a conflicting external value untouched;
3. after a subsequent clean enable it can adopt that external value as the new baseline;
4. later disable restores that adopted external baseline rather than the older vanilla value.

Multiplayer authority/client behavior remains unvalidated and is the next release boundary.
