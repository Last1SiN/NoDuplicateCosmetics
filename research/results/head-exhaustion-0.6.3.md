# Head exhaustion propagation — probe 0.6.3

Verdict: **PARTIAL PASS; one baseline summary still missing for strict same-run ratio comparison**.

Runtime log: `unrealsdk(20260911-152323).log`.

## Plan and mutation safety

The corrected console dispatcher worked. The runtime plan resolved exactly:

- 24 direct stock character-head leaves (4 class pools x 6 leaves)
- 6 Siren leaves
- one exact `ItemPool_SkinsAndMisc -> Heads` parent edge at index 0
- 25 total captured signatures

All 24 head leaves were simple positive constant weights (`BaseValueConstant=1.0`, no DataTable, BaseValueAttribute, or AttributeInitializer). The world-root Heads edge was also a simple constant (`BaseValueConstant≈0.05`).

Synthetic exhaustion applied successfully and runtime verification reported `good=25 bad=0`. Exact guarded restore later also reported `good=25 bad=0` and `RESTORE PASS exact signatures restored records=25`.

## Dedicated-pool evidence

The direct Siren baseline request batch was 64. The log contains 64 `HEAD_HIT batch=siren_baseline` events spanning all six Siren heads, proving the stock dedicated leaf pool normally resolves direct requests.

After synthetic exhaustion, a 64-request `siren_exhausted` batch was started. There are no cosmetic/head hit events between that batch start and the subsequent world batch. This is strong evidence for dedicated-empty -> no replacement cosmetic, but step 7 (`BATCH_SUMMARY`) was skipped, so the formal `observed=0` summary was not captured.

## World propagation evidence

The propagated world batch after excluding the exhausted Heads branch produced:

- requests: 384
- observed cosmetics: 160
- observed ratio: `0.4167`
- head hits: `0`
- Siren hits: `0`
- distinct cosmetics: 45

This proves the exhausted Heads category did not leak back into the broader world source and other source-local cosmetic branches continued to resolve.

However, step 2 (same-run world baseline summary) was skipped. Therefore the strict same-run comparison of baseline vs propagated `observed_ratio` is unavailable from this log. The prior 0.5.0 world baseline was `0.3984`, which is consistent with `0.4167`, but that cross-run comparison is supporting evidence rather than a strict same-run PASS.

## Missing evidence / minimal recovery

The full mutation sequence does not need to be repeated. After the successful restore, run only:

1. `ndcprobe 1`
2. wait 3–5 seconds
3. `ndcprobe 2`

This captures a clean post-restore world baseline ratio in the same runtime implementation. The direct exhausted-Siren semantics are already strongly evidenced by the absence of any hits after the 64-request exhausted batch, though a later dedicated-empty summary could be captured if strict formal closure is desired.
