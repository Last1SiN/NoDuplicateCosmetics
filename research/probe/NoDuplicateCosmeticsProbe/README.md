# NoDuplicateCosmeticsProbe 0.4.0

Bounded mutation probe for NoDuplicateCosmetics.

This probe deliberately modifies exactly one stock loot-pool leaf entry in memory: the already-unlocked Siren head **Motosaurus** in `ItemPool_Customizations_Heads_Loot_Siren`.

It does **not** modify profile data, pool `Quantity`, parent `PoolProbability`, any non-target entry, or any unrelated loot pool.

The probe fails closed unless:

- Motosaurus is reported as already unlocked by the local profile;
- the exact stock Motosaurus balance is present in the exact Siren head pool;
- the target `Weight` is a simple constant weight with no DataTable, attribute, or initializer.

Only `Weight.BaseValueConstant` is changed from its captured stock value to `0.0`. All other fields are left untouched. Disable restores the captured value only if the current weight still matches the probe-owned state.

## Test sequence

Wait until fully in-game.

1. NumPad 0 — inspect target and capture stock weight.
2. NumPad 1 — spawn 96 baseline rolls from the exact Siren head pool.
3. Wait 2–3 seconds, then NumPad 2 — baseline summary.
4. NumPad 3 — apply Motosaurus exclusion.
5. NumPad 4 — spawn 96 filtered rolls.
6. Wait 2–3 seconds, then NumPad 5 — filtered summary.
7. NumPad 6 — restore the exact captured target weight.
8. NumPad 7 — spawn 96 restored rolls.
9. Wait 2–3 seconds, then NumPad 8 — restored summary.
10. NumPad 9 — verify current target weight at any time.

Expected success pattern:

- baseline: Motosaurus appears at least once;
- filtered: Motosaurus appears zero times;
- filtered observed-result count remains comparable to baseline, showing that the resolver redistributes selection among remaining positive entries instead of converting the removed weight into a no-drop slot;
- restored: Motosaurus can appear again;
- `RESTORE PASS exact weight signature restored` is logged.

This is not a release build.
