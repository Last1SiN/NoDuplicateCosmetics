# Pool exhaustion propagation — probe 0.6.0 plan

Goal: establish two missing resolver semantics without touching profile ownership.

Synthetic target: stock ECHO cosmetic pool, chosen because it is a direct-leaf child of `ItemPool_SkinsAndMisc` and its world-root parent edge is expected to be a simple constant weight.

Test boundaries:

1. Capture all ECHO leaf weights and the exact world-root edge to the ECHO pool.
2. Baseline the world root and the dedicated ECHO pool separately.
3. Set every ECHO leaf weight to zero while leaving `Quantity` untouched.
4. Directly roll the exhausted ECHO pool; expected result is zero cosmetics rather than a foreign replacement.
5. Set only the world-root ECHO branch weight to zero.
6. Roll the world root again; ECHO hits must be zero while the root observed/no-drop ratio remains comparable to baseline and other existing branches continue to resolve.
7. Restore all captured signatures exactly.

The probe must fail closed before mutation if any touched weight is not a simple positive constant or if exact target discovery is ambiguous.
