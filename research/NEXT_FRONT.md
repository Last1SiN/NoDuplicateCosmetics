# Next bounded front

The attribute-backed leaf exclusion boundary is closed, and the first production-shaped implementation candidate now exists on `implementation/stock-world-filter-v0.1`.

## Candidate under test

`NoDuplicateCosmetics` version `0.1.0` filters only the stock world-cosmetic graph rooted at `ItemPool_SkinsAndMisc`.

It implements the runtime-confirmed contracts:

1. Simple constant owned leaves: set `BaseValueConstant = 0`.
2. Attribute-backed owned leaves of the proven shape: set both `BaseValueConstant = 0` and `BaseValueScale = 0`, preserving `BaseValueAttribute` and all other fields.
3. Exhausted child pools propagate upward only through the same source-local graph.
4. Root `Quantity`, external `PoolProbability`, profile data, non-cosmetic entries, and foreign pools remain untouched.
5. Ownership is refreshed lazily during the session so newly learned cosmetics can become ineligible without restart.
6. Exact guarded restore is used for every managed weight; later third-party changes are left untouched rather than overwritten.
7. Unsupported or unresolved weight/ownership shapes fail closed.

The implementation contains no dev spawner, keybinds, console commands, or normal-operation info logging.

## Current validation boundary

Runtime-test the release-shaped candidate itself, not another mutation probe.

Required first-pass validation:

- game loads cleanly with the candidate enabled;
- no errors from `NoDuplicateCosmetics` appear after entering a character;
- world cosmetic drops continue to occur normally;
- the known owned world-drop head `Motosaurus` is not selected while the candidate is active;
- unowned cosmetics still appear from the same world source;
- disabling the mod does not crash and guarded restore emits no errors;
- after learning a previously-unowned world cosmetic during the same session, wait at least one refresh interval and verify it stops being selected without restarting.

Use a separate development-only stock-pool spawner if rapid sampling is needed; do not add diagnostic spawning back into the production candidate.

## After candidate PASS

Broaden discovery from the single stock world root to exact mission/dedicated/container/DLC cosmetic sources while preserving each source's own reachability graph. Do not claim generic all-source coverage before those source topologies are enumerated and validated.

Multiplayer authority/client behavior and deeper compatibility arbitration remain separate later fronts.
