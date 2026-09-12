# Same-session unlock refresh — PASS

Validator: `NoDuplicateCosmeticsUnlockRefreshValidator 0.3.1`
Production: `NoDuplicateCosmetics 0.2.0`

## Runtime result

The corrected validator first proved that a real dropped pickup actor existed for the selected one-item mission cosmetic source, then transferred that exact pickup into the player inventory without changing profile ownership.

Observed target:

- pool: `/Game/Gear/WeaponTrinkets/_Design/ItemPools/ItemPool_Customizations_WeaponTrinkets_Mission_28.ItemPool_Customizations_WeaponTrinkets_Mission_28`
- balance: `/Game/Gear/WeaponTrinkets/_Design/TrinketParts/WeaponTrinket_28.InvBal_WeaponTrinket_28`
- ownership class: `OakInventoryCustomizationPartData`
- weight mode before ownership: `constant`
- physical pickup actor: `/Game/Maps/Sanctuary3/Sanctuary3_P.Sanctuary3_P:PersistentLevel.BP_OakInventoryItemPickup_C_0`
- pickup initialized: `True`
- pickup active: `True`
- pickup spawn paused: `False`
- validator transferred the confirmed pickup to inventory with `GiveInventoryToUser`

After the player used the trinket normally:

- native ownership transitioned `False -> True` in the same running session;
- production changed the target leaf to the proven filtered signature after `384.6 ms`;
- no game restart or map reload occurred;
- validator then issued `32` requests against the same exact one-item dedicated pool;
- `target_hits=0`;
- validator profile mutation remained `NONE`;
- final verdict: `AUTO_VERDICT PASS`.

Production initialization on the same run remained clean:

- `loaded_pools=717`;
- `cosmetic_leaves=218`;
- `mapped_cosmetic=218`;
- `unmapped_cosmetic=0`;
- initial `owned=1` / `filtered_leaves=1`;
- `unsupported_owned=0`;
- `ownership_unresolved=0`;
- `blocked=0`;
- `cycles=0`.

## Conclusion

The 1-second ownership refresh loop is sufficient for a real same-session unlock transition in the tested dedicated cosmetic source. Production notices the native ownership change without restart, disables the exact newly-owned leaf, and the exhausted single-item pool subsequently produces no target result.

This closes the same-session real ownership refresh boundary for the tested constant-weight dedicated source.

## Still outside this result

- disable / normal guarded restore;
- multiplayer authority/client behavior;
- compatibility arbitration when an external mod changes a managed weight after filtering;
- same-session unlock of every possible cosmetic class/weight topology.
