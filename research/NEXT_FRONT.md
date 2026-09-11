# Next bounded front

Build and test a stock-world recursive owned-cosmetic filter candidate.

Boundary:

- start from `ItemPool_SkinsAndMisc` only;
- traverse only vanilla child pools reachable from that root;
- classify direct cosmetic leaves by the three runtime-confirmed ownership APIs;
- zero only owned simple-constant leaf weights;
- do not alter `Quantity`, `PoolProbability`, or non-cosmetic entries;
- preserve source-local reachability;
- capture and ownership-guard every touched weight for exact restore;
- perform ownership evaluation only after local player/profile readiness;
- log unresolved/non-simple entries and fail closed on them;
- measure native no-drop rate before and after filtering;
- do not generalize to arbitrary dedicated/mission/shared pools until this world-root front passes.