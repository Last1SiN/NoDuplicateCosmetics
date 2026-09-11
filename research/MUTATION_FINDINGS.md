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

## 0.5.0 recursive stock-world owned filter

Verdict: **PASS for the tested stock world graph and currently-owned leaves**.

Runtime facts:

1. Recursive traversal from the exact vanilla `ItemPool_SkinsAndMisc` root resolved 20 reachable pools and 139 cosmetic leaf entries.
2. The test profile had one owned leaf among those 139: Siren head `Motosaurus`.
3. Baseline: 384 requests -> 153 observed cosmetics (`0.3984`), one owned hit, zero unresolved hits.
4. Filtered: 384 requests -> 154 observed cosmetics (`0.4010`), zero owned hits, zero unresolved hits.
5. The essentially unchanged observed ratio establishes that source-local leaf exclusion does not disturb the world root's native `Quantity`/no-drop behavior when the containing child pool remains non-empty.
6. Guarded exact restore passed; post-restore manual verification reported `good=1 bad=0`.
7. The restored random batch did not happen to roll Motosaurus again; this does not contradict restore because the exact captured signature was independently verified after restore.

Full evidence: `research/results/world-owned-filter-0.5.0.md`.

## Next boundary

The remaining stock-world mutation boundary is **pool/category exhaustion propagation**.

A bounded synthetic exhaustion experiment is permitted because its purpose is to establish resolver semantics, not to model profile ownership. It must:

- choose one exact vanilla cosmetic child pool reachable from `ItemPool_SkinsAndMisc`;
- capture every touched leaf and parent-edge weight before mutation;
- first prove that directly rolling the fully exhausted dedicated child pool produces no replacement cosmetic;
- then make that exhausted child branch ineligible in the broader world root and prove the parent continues to resolve among its remaining source-local branches;
- preserve the world root's original `Quantity`/no-drop behavior;
- never add entries or redirect to foreign pools;
- restore every touched signature exactly and ownership-guard the restore.

Only after this boundary passes should the implementation generalize exhaustion propagation recursively or expand to arbitrary dedicated/mission/shared sources.