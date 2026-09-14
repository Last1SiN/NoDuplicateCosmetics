# Disable / normal restore 0.4.0 — PASS

Production candidate: `NoDuplicateCosmetics 0.2.0`
Validator: `NoDuplicateCosmeticsDisableRestoreValidator 0.4.0`

## Verdict

**PASS** for the exercised owned one-item mission trinket leaf.

## Runtime evidence

Target:

`/Game/Gear/WeaponTrinkets/_Design/TrinketParts/WeaponTrinket_28.InvBal_WeaponTrinket_28`

Observed sequence:

- production initialized cleanly with `717` loaded pools, `218` mapped cosmetic leaves, `owned=2`, `filtered_leaves=2`, and zero unsupported/unresolved/blocked/cycle counts;
- validator selected the owned target while it was in the production-disabled weight signature;
- `production.disable(dont_update_setting=True)` executed the real production `on_disable -> _restore_all` path;
- the target returned to a supported positive constant weight after `94.2 ms`;
- one hidden stock request from the exact one-item pool resolved the target (`target_hits=1`), proving the restored weight was operational in the native resolver;
- production was re-enabled in the same process;
- the target returned to the expected filtered signature after `2216.9 ms`;
- 16 post-filter requests from the same one-item pool produced `target_hits=0`;
- production was left enabled;
- persistent enabled state was not changed.

Final validator line reported:

`AUTO_VERDICT PASS ... restored_roll_hits=1 ... post_filter_target_hits=0 production_left_enabled=YES validator_weight_mutation=NONE persistent_enable_setting_changed=NO`

## Scope

This validates ordinary lifecycle restore/re-filter behavior only. External third-party weight conflict arbitration is covered separately.
