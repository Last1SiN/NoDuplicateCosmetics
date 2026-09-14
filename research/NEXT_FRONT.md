# Next bounded front

The generalized loaded-pool selection boundary, same-session real ownership refresh, normal disable/restore lifecycle, and external-conflict compatibility arbitration are closed for the exercised cases.

Evidence:

- `research/results/generic-topology-validator-0.2.1-pass.md`
- `research/results/same-session-unlock-refresh-0.3.1-pass.md`
- `research/results/disable-restore-0.4.0-pass.md`
- `research/results/compatibility-arbitration-0.5.0-pass.md`
- `research/results/multiplayer-scope-decision.md`

Confirmed with `NoDuplicateCosmetics 0.2.0`:

- representative dedicated, nested, mixed, and stock-world source-local selection semantics passed;
- a real cosmetic was learned in-session and the exact leaf was filtered without restart;
- ordinary disable restored a managed leaf to an operational positive weight and re-enable filtered it again;
- a deliberate later external weight change was not overwritten while production remained enabled;
- guarded restore preserved the conflicting external value;
- on a subsequent clean enable production adopted that external value as the new baseline, filtered it, and later restored the same external baseline;
- cleanup returned the exercised target to the vanilla baseline beneath the production filter;
- production was left enabled after each validator front.

## Multiplayer scope

Co-op support is intentionally **out of scope for this release** by product-owner decision.

Do not run or require the real two-peer matrix before release. This does not prove incompatibility; it means multiplayer behavior is unvalidated and must not be advertised as supported.

Keep `coop_support = "Unknown"` and describe the validated scope as single-player/local-player only. If co-op becomes a future requirement, reopen the multiplayer authority/client front and run the host/client matrix then.

## Current bounded front: release cleanup

1. Remove validation-only normal INFO diagnostics from production while retaining error reporting.
2. Remove candidate wording and finalize README_EN / README_RU around the actually validated single-player scope.
3. Preserve `coop_support = "Unknown"`; do not claim co-op support.
4. Reconcile release version/metadata using numeric dotted versioning only.
5. Verify production still contains no `SpawnLootAsync`, commands/keybinds, profile ownership writes, or `Quantity` / `PoolProbability` writes.
6. Build a canonical `.sdkmod` with exactly one matching root folder and the expected five files.
7. Build the Nexus outer ZIP containing the canonical `.sdkmod`, README_EN.md, README_RU.md, and LICENSE.
8. Reopen archives and verify compile, metadata, documentation, file layout, and SHA256 before sharing.

After release cleanup passes, the current single-player release is ready for publication. Multiplayer can be a separate future milestone.
