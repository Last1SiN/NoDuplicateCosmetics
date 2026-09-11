# Next bounded front

Continue the **stock cosmetic child-pool exhaustion propagation** experiment, but do not mutate attribute-backed weights yet.

Probe 0.6.0 rejected the ECHO target before mutation because its first leaf uses the rarity attribute `Att_RarityWeight_05_Legendary`. That fail-closed result is now part of the evidence and attribute-backed leaf mutation is a separate later front.

Use the stock Heads branch for the corrected constant-only experiment:

- discover the four character-specific head leaf pools reachable from the stock Heads selector;
- fail closed unless all 24 direct head leaves are simple positive constant weights;
- capture exact full signatures for those 24 leaves and for the exact `ItemPool_SkinsAndMisc -> Heads` edge;
- do not mutate the attribute-driven intermediate Heads->class selector;
- baseline the world root and the exact Siren head leaf pool separately;
- synthetically exhaust all 24 head leaves;
- directly roll the exhausted Siren head pool and require no cosmetic result;
- make only the exact world-root Heads branch ineligible, then roll `ItemPool_SkinsAndMisc` and require zero head hits while preserving the root's native Quantity/no-drop ratio;
- never alter `Quantity`, `PoolProbability`, profile ownership, non-cosmetic entries, or foreign pools;
- restore all 25 captured signatures exactly with a mutation-ownership guard.

PASS here establishes dedicated-empty semantics and broader-source exhaustion propagation without conflating them with attribute-expression mutation. After that, open a separate bounded front for attribute-backed leaf weights.