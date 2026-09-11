# NoDuplicateCosmeticsProbe 0.5.0

Bounded recursive world-cosmetic mutation probe for NoDuplicateCosmetics.

Scope is deliberately limited to the vanilla `ItemPool_SkinsAndMisc` graph. The probe recursively discovers only pools reachable from that exact root, resolves all direct cosmetic leaves through the three runtime-confirmed ownership APIs, and zeros only already-owned leaf entries which use a simple positive constant weight.

It does not change any `Quantity`, parent `PoolProbability`, non-cosmetic entry, profile data, or foreign loot pool. If a reachable direct leaf pool would become completely empty, or if an owned leaf cannot be resolved safely, the whole mutation plan fails closed before any write is made. Parent exhaustion behavior is a later boundary.

The profile scan is lazy. Probe 0.4.0 showed that early module-enable ownership queries can be false before the normal player/profile state is ready.

## Test sequence

Wait until fully in-game.

1. NumPad 0 — build/log the recursive world ownership plan.
2. NumPad 1 — spawn 384 baseline world-cosmetic requests.
3. Wait 3–5 seconds, NumPad 2 — baseline summary.
4. NumPad 3 — apply all safe owned-leaf exclusions.
5. NumPad 4 — spawn 384 filtered world-cosmetic requests.
6. Wait 3–5 seconds, NumPad 5 — filtered summary.
7. NumPad 6 — guarded exact restore.
8. NumPad 7 — spawn 384 restored requests.
9. Wait 3–5 seconds, NumPad 8 — restored summary.
10. NumPad 9 — verify every captured weight.

Send `unrealsdk.log`.

Success criteria:

- plan resolves without blockers;
- baseline contains one or more `owned_hits`;
- filtered has `owned_hits=0`;
- filtered observed ratio remains statistically comparable to baseline, showing that owned-leaf filtering did not remove the stock root's native Quantity/no-drop behavior;
- restore reports exact signatures restored;
- restored owned hits return.

This is not a release build.
