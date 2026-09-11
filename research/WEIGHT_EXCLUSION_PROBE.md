# Owned-weight exclusion probe 0.4.0

Status: ready for runtime validation.

## Question

Does BL3 re-normalize the remaining positive `BalancedItems` weights when one already-owned cosmetic leaf entry is made ineligible by setting its simple constant `Weight.BaseValueConstant` to `0.0`, or does the removed weight become an implicit no-drop slot?

This is the last bounded behavior question before generalizing source-local filtering.

## Scope

The probe mutates exactly one stock leaf entry in memory:

- pool: `/Game/Pickups/Customizations/_Design/ItemPools/Heads/ItemPool_Customizations_Heads_Loot_Siren.ItemPool_Customizations_Heads_Loot_Siren`
- target customization: `/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/CustomHead_Siren_4.CustomHead_Siren_4`
- target balance: `/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/CustomHead_Siren_4.InvBal_CustomHead_Siren_4`
- display name: `Motosaurus`

Previous runtime evidence already showed this customization as `owned=YES` on the current test profile. Public game-data references identify the same asset as Motosaurus, and existing BL3 pool definitions represent the target balance as a direct weighted entry.

## Safety gates

The mutation fails closed unless runtime confirms all of the following:

1. Motosaurus is still reported as unlocked by `AOakPlayerController.IsCustomizationUnlocked(...)`.
2. The exact target balance is present in the exact stock Siren head pool.
3. The target weight is a simple constant form: positive `BaseValueConstant`, no `DataTable`, no `BaseValueAttribute`, and no `AttributeInitializer`.
4. The complete observed weight signature matches the captured baseline immediately before mutation.

Only `Weight.BaseValueConstant` is changed to `0.0`. `Quantity`, `PoolProbability`, parent pools, sibling entries, profile data, and non-cosmetic data are not touched.

## Restoration ownership

The probe records the complete observable `FAttributeInitializationData` signature:

- `BaseValueConstant`
- `DataTableValue.DataTable`
- `DataTableValue.RowName`
- `DataTableValue.ValueName`
- `BaseValueAttribute`
- `AttributeInitializer`
- `BaseValueScale`

Restore is performed only if the current weight still equals the probe-owned state `(BaseValueConstant=0.0 + all original remaining fields)`. If another mutation changes the entry while the probe owns it, restore fails closed instead of clobbering that change.

Disable automatically attempts the same guarded restore.

## Runtime test

The probe uses the exact Siren head leaf pool for all three distributions. Each batch sends 96 stock `SpawnLootAsync` requests and counts only balances reachable from that exact target pool.

1. NumPad 0 — inspect/capture target.
2. NumPad 1 — baseline 96 rolls.
3. NumPad 2 — baseline summary.
4. NumPad 3 — apply target exclusion.
5. NumPad 4 — filtered 96 rolls.
6. NumPad 5 — filtered summary.
7. NumPad 6 — guarded restore.
8. NumPad 7 — restored 96 rolls.
9. NumPad 8 — restored summary.
10. NumPad 9 — manual current-weight verification.

## PASS criteria

- Baseline produces at least one Motosaurus hit.
- Filter application re-reads the live target entry and confirms only `BaseValueConstant` changed to `0.0`.
- Filtered batch produces zero Motosaurus hits.
- Filtered observed-result count remains comparable to baseline rather than losing approximately the target item's original selection share; this is evidence that the resolver re-normalizes remaining positive entries.
- Guarded restore returns the complete weight signature to the captured baseline.
- Restored batch can produce Motosaurus again.

If filtered total output falls by roughly the removed entry's share, zero-weight mutation alone is insufficient for production reroll semantics and the architecture must move to a different pre-selection interception mechanism.
