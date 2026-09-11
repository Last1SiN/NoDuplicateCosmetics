# Head exhaustion propagation — probe 0.6.1 plan

Probe 0.6.0 correctly rejected ECHO because the first ECHO leaf uses an attribute-backed rarity weight. 0.6.1 keeps the same exhaustion-propagation question but removes that extra unknown from the experiment.

Synthetic scope:

- exact stock world root `ItemPool_SkinsAndMisc`;
- all four stock class-specific head leaf pools;
- exactly 24 direct head leaf entries, each required at runtime to be a simple positive constant weight;
- exact `ItemPool_SkinsAndMisc -> Heads` parent edge, also required to be a simple positive constant;
- the intermediate Heads->class attribute-driven selector remains read-only.

Test:

1. Baseline 384 world-root requests.
2. Baseline 64 direct Siren-head requests.
3. Zero all 24 direct head leaf constants and the exact world-root Heads edge.
4. Directly roll the exhausted Siren leaf pool; expected `observed=0`.
5. Roll the world root; expected `head_hits=0` while the root observed/no-drop ratio remains comparable to baseline.
6. Restore all 25 captured signatures exactly.

No Quantity, PoolProbability, profile ownership, foreign pool, non-cosmetic entry, or attribute-driven weight is mutated.

PASS establishes dedicated-empty semantics and broader-source exhaustion propagation. Attribute-backed leaf exclusion remains a separate subsequent front.