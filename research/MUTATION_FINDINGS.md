# Mutation findings

## 0.4.0 single-leaf exclusion

Verdict: **PASS**.

The bounded Motosaurus experiment establishes the following runtime facts for a stock direct `ItemPoolData` cosmetic leaf:

1. An owned cosmetic entry with a simple constant `Weight` can be made ineligible by setting only `Weight.BaseValueConstant` to `0.0`.
2. The exact 96/96 baseline pool continued to resolve 96/96 results after one of six equal positive-weight entries was zeroed.
3. The removed cosmetic went from 12/96 hits to 0/96 hits.
4. The remaining five entries absorbed the selection probability; the removed weight did not become a no-drop slot.
5. Restoring the captured constant restored the exact full observed weight signature and made the cosmetic selectable again (12/96 in the restored run).
6. Early module-enable ownership lookup is not authoritative: the same session returned not-owned during startup and owned later after normal player/profile state was available. Production must filter lazily/after readiness and must be able to refresh.

Full evidence: `research/results/owned-weight-exclusion-0.4.0.md`.

## Next boundary

The next probe may expand from one direct leaf to the stock world-cosmetic graph, but it must retain these constraints:

- ownership-driven only;
- source-local reachability only;
- no changes to `Quantity` or parent `PoolProbability`;
- no new entries and no redirection to foreign pools;
- capture before mutation;
- ownership-guarded exact restore;
- delayed/lazy ownership evaluation after local profile readiness;
- explicit test of nested child-pool exhaustion before production generalization.