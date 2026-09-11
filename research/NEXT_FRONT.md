# Next bounded front

Build and test a **stock cosmetic child-pool exhaustion propagation** probe.

Use one exact vanilla child pool reachable from `ItemPool_SkinsAndMisc`; prefer a direct-leaf category whose parent edge in the world root is a simple constant weight so the first propagation experiment has no attribute-expression ambiguity.

Boundary:

- synthetic exhaustion is allowed only to establish resolver semantics; do not alter profile ownership;
- capture exact full weight signatures for every touched leaf and parent edge;
- do not alter `Quantity`, `PoolProbability`, non-cosmetic entries, or foreign pools;
- first set all leaves of the exact dedicated cosmetic child pool ineligible and directly roll that exact pool;
- expected direct-pool behavior: no eligible cosmetic means no replacement drop;
- then set only that exhausted child branch in the broader `ItemPool_SkinsAndMisc` parent ineligible;
- roll the world root before/after propagation and verify the exhausted category disappears while the parent's native no-drop ratio remains comparable;
- parent resolution may use only remaining branches already reachable from that exact world root;
- never add entries or redirect to another pool;
- restore every touched leaf and parent-edge signature exactly with a mutation-ownership guard;
- do not yet generalize to complex attribute-driven parent edges, arbitrary mission/dedicated sources, or production code.

PASS requires both dedicated-empty semantics and parent-reroll semantics to be runtime-confirmed.