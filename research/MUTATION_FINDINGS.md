# Mutation findings

## 0.4.0 single-leaf exclusion

Verdict: **PASS**.

A stock direct cosmetic leaf with a simple constant weight can be made ineligible by setting only `Weight.BaseValueConstant = 0`. In the bounded Motosaurus test the target moved from 12/96 hits to 0/96 while the pool still resolved 96/96 results, proving native sibling-weight renormalization rather than conversion of the removed weight into a no-drop slot. Exact guarded restore passed.

The same run also showed that ownership lookup at early module enable is not authoritative; filtering must be lazy/refreshable after player/profile state is ready.

Full evidence: `research/results/owned-weight-exclusion-0.4.0.md`.

## 0.5.0 recursive stock-world owned filter

Verdict: **PASS for the tested stock world graph and currently-owned leaves**.

Traversal from exact vanilla `ItemPool_SkinsAndMisc` resolved 20 reachable pools and 139 cosmetic leaves. The test profile had one owned leaf (`Motosaurus`). Baseline produced 153/384 cosmetics (`0.3984`) with one owned hit; filtered produced 154/384 (`0.4010`) with zero owned hits and zero unresolved hits. Native root `Quantity`/no-drop behavior therefore remained intact while the containing child pool stayed non-empty. Exact restore passed.

Full evidence: `research/results/world-owned-filter-0.5.0.md`.

## 0.6.0 ECHO exhaustion target

Verdict: **BOUNDED REJECT FOR THIS TARGET; FAIL-CLOSED PASS**.

The first tested stock ECHO leaf was attribute-backed (`BaseValueConstant=1`, rarity `BaseValueAttribute`, `BaseValueScale=1`). The constant-only exhaustion probe correctly refused to mutate this unproven shape. This established that cosmetic weights are not uniformly constant-only.

Full evidence: `research/results/pool-exhaustion-0.6.0.md`.

## 0.6.3 constant-only head exhaustion and propagation

Verdict: **PASS for exhaustion semantics; world-root rate comparison remains statistical rather than exact**.

All 24 stock character-head leaves and the exact world-root `Heads` edge were simple constants and were mutated/restored exactly. A direct Siren-head pool produced 64/64 results before exhaustion and no head events after all six Siren leaves were zeroed, supporting dedicated-empty -> no replacement cosmetic. With the exhausted Heads category propagated out of `ItemPool_SkinsAndMisc`, world rolls produced zero head hits while other source-local cosmetic branches continued resolving. Exact restore passed for all 25 touched signatures.

Across available runs the world observed ratio remained in the same broad native range, but finite-sample variation was visible; production validation should use larger-N stress testing rather than claim an exact invariant from one 384-roll comparison.

Full evidence: `research/results/head-exhaustion-0.6.3.md`.

## 0.7.0 / 0.7.4 attribute-backed leaf exclusion

Verdict: **PASS**.

Probe 0.7.4 automatically selected a direct stock ECHO leaf with this live shape:

- `BaseValueConstant = 1.0`
- non-null rarity `BaseValueAttribute`
- no DataTable
- null `AttributeInitializer`
- `BaseValueScale = 1.0`

Runtime batches:

- baseline: 128/128 observed, target 26 hits;
- `BaseValueConstant = 0` only: 128/128 observed, target 25 hits;
- `BaseValueConstant = 0` plus `BaseValueScale = 0`: 128/128 observed, target 0 hits.

Therefore `BaseValueConstant = 0` alone is **not** a valid exclusion operation for this attribute-backed shape. Zeroing both constant and scale excludes the target while native selection continues among sibling ECHO entries. Both mutation phases restored the exact captured signature, and the final verification matched the original weight.

Probe 0.7.3 was retired after a native access violation caused by an unsafe design which could call `SpawnLootAsync` from inside `InventoryBalanceStateComponent:PostBeginPlay`, re-entering inventory construction. 0.7.4 moved all mutation/spawn/state-transition work to a normal HUD-frame driver and kept the construction hook observation-only; that run completed successfully.

Full evidence: `research/results/ATTRIBUTE_WEIGHT_0_7_4_PASS.md`.

## Proven production mutation contract

For the stock world-cosmetic graph, the following operations are now runtime-supported:

1. **Simple constant leaf:** set `BaseValueConstant = 0`.
2. **Attribute-backed leaf with positive constant + non-null BaseValueAttribute + null AttributeInitializer + no DataTable + positive scale:** set both `BaseValueConstant = 0` and `BaseValueScale = 0`, preserving the attribute pointer and all other fields.
3. Preserve source `Quantity` and parent `PoolProbability`.
4. Preserve source-local graph reachability; never redirect to foreign cosmetic pools.
5. Propagate fully exhausted child branches upward only within the original source graph.
6. Restore exact captured signatures only when the current live state still matches the mod-owned filtered state.
7. Fail closed on unproven DataTable-backed, AttributeInitializer-backed, unresolved, or otherwise unfamiliar weight shapes.

The next front is a production-shaped stock-world filter with lazy ownership readiness/refresh and no diagnostic spawner. See `research/NEXT_FRONT.md`.
