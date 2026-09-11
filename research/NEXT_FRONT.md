# Next bounded front

The constant-only head exhaustion experiment is almost closed. Do **not** repeat the full mutation sequence.

0.6.3 established:

- all 24 direct stock character-head leaves are simple positive constants;
- the exact `ItemPool_SkinsAndMisc -> Heads` edge is a simple constant;
- all 25 targeted signatures can be zeroed and restored exactly;
- a 64-request direct Siren baseline produced 64 heads;
- the subsequent 64-request exhausted Siren batch emitted no cosmetic/head events before the next batch began;
- the propagated world batch produced `160/384` cosmetics (`0.4167`) with `head_hits=0` and `siren_hits=0`;
- exact restore passed for all 25 signatures.

The only strict evidence missing is the same-run world baseline ratio because console step 2 was skipped before the next batch reset the counters.

## Minimal recovery

After the successful restore, run only:

1. `ndcprobe 1`
2. wait 3–5 seconds
3. `ndcprobe 2`

Compare that clean baseline ratio against propagated `0.4167`. If comparable, close broader-source exhaustion propagation as PASS.

Do not mutate attribute-backed weights in this recovery. After closure, open a separate bounded front for attribute-backed leaf eligibility/exclusion semantics (for example the ECHO rarity-weight case discovered by 0.6.0).