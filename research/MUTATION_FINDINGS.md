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

## 0.6.0 ECHO exhaustion target

Verdict: **BOUNDED REJECT FOR THIS TARGET; FAIL-CLOSED PASS**.

The first stock ECHO leaf was not constant-only. Its runtime weight contained `BaseValueAttribute=/Game/GameData/Loot/RarityWeighting/Att_RarityWeight_05_Legendary.Att_RarityWeight_05_Legendary` in addition to `BaseValueConstant=1.0` and `BaseValueScale=1.0`. Because 0.6.0 deliberately did not claim safe semantics for attribute-backed weights, it rejected the plan before spawning or mutation. No game state was changed.

This establishes a new production boundary: cosmetic leaf weights are not uniformly constant-only. Attribute-backed leaves require their own source/runtime proof before they can be made ineligible safely.

Full evidence: `research/results/pool-exhaustion-0.6.0.md`.

## Next boundary

Continue the **pool/category exhaustion propagation** experiment with a constant-only synthetic target rather than broadening mutation semantics prematurely.

Use the stock character-head leaf pools:

- fail-closed validate all 24 direct class-head leaves as simple positive constants;
- zero those leaves only for the synthetic exhaustion experiment;
- leave the attribute-driven intermediate Heads->class selector untouched;
- directly roll the exhausted Siren head pool and require zero cosmetic results;
- zero only the exact simple `ItemPool_SkinsAndMisc -> Heads` edge for world propagation;
- roll the world root and require zero head hits while preserving the root Quantity/no-drop ratio;
- restore every captured leaf and root-edge signature exactly.

Only after exhaustion propagation itself passes should attribute-backed leaf-weight exclusion become a separate bounded front.