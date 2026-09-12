# Next bounded front

The generalized loaded-pool selection boundary and the same-session real ownership refresh boundary are now closed for the exercised cases.

Evidence:

- `research/results/generic-topology-validator-0.2.1-pass.md`
- `research/results/same-session-unlock-refresh-0.3.1-pass.md`

Confirmed with `NoDuplicateCosmetics 0.2.0`:

- representative dedicated, nested, mixed, and stock-world source-local selection semantics passed;
- a real one-item mission trinket pickup was physically created and transferred into inventory;
- the player learned that trinket normally, causing native ownership `False -> True`;
- production filtered the newly-owned exact leaf in the same running session after `384.6 ms`;
- 32 requests from the now-exhausted dedicated pool produced `target_hits=0`;
- no validator profile mutation occurred.

## Current bounded front: disable / normal guarded restore

Validate production lifecycle ownership around a real managed leaf without changing persistent mod settings.

Use a separate development-only validator which may drive the `mods_base.Mod` enable/disable methods, but must not write the target weight directly.

Preferred fully automatic flow:

1. After player readiness, find the running `NoDuplicateCosmetics` mod instance through `mods_base.get_ordered_mod_list()` and require it to be enabled.
2. Select an owned cosmetic leaf from a known one-item dedicated pool which is currently in the production-filtered signature.
3. Record the filtered signature.
4. Call `production.disable(dont_update_setting=True)` so production executes its real `on_disable -> _restore_all` path without changing persistent enable settings.
5. Require the target leaf to return to a supported positive eligible signature within a bounded window; record this as the restored/original signature.
6. Optionally issue one bounded request from the exact one-item pool while production is disabled and require the target to resolve, proving the restored weight is operational in the native resolver.
7. Call `production.enable()` in the same session.
8. Require the exact target leaf to return to the expected filtered signature computed from the observed restored signature.
9. After settling, issue a bounded request set from the same dedicated pool and require zero target results again.
10. On validator failure or validator disable, always make a best-effort attempt to leave production enabled.
11. The validator must not mutate `BaseValueConstant`, `BaseValueScale`, pool `Quantity`, source probabilities/counts, profile ownership, or production internal state directly.

This front validates the ordinary restore path. It does **not** yet inject a third-party conflicting weight.

## Boundary after disable / normal restore

If this passes, proceed to:

1. multiplayer authority/client behavior;
2. compatibility arbitration / external-conflict guarded restore, where a separate test component changes a production-managed weight after filtering and production must leave that external value untouched rather than restoring over it.
