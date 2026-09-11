# NoDuplicateCosmetics 0.1.2 Candidate

First production-shaped candidate for Borderlands 3.

## Current scope

This candidate filters the vanilla world-cosmetic graph rooted at `ItemPool_SkinsAndMisc`.
It is intentionally not yet advertised as covering every mission, dedicated, container,
or DLC-specific cosmetic source.

## Behavior

- Already-owned cosmetics become ineligible before the game's native weighted selection.
- Rerolls remain inside the original source-reachable loot graph.
- Cosmetics are never replaced with an extra weapon roll.
- The source pool's native `Quantity`/no-drop behavior is left untouched.
- If a child cosmetic pool becomes exhausted, only that exact source-local child branch
  is made ineligible; exhaustion can propagate upward inside the same graph.
- If the whole world-cosmetic root is exhausted, the cosmetic roll can resolve to no item.
- Newly learned cosmetics are picked up by a lazy ownership refresh without restarting.

## Safety / compatibility policy

The candidate only mutates runtime `FAttributeInitializationData` shapes which have been
verified in-game:

- simple constant weight: `BaseValueConstant -> 0`;
- attribute-backed weight with no DataTable/AttributeInitializer: both
  `BaseValueConstant -> 0` and `BaseValueScale -> 0`, preserving the attribute pointer.

Unknown weight shapes fail closed. `Quantity`, `PoolProbability`, profile data,
non-cosmetic entries, and foreign pools are never modified.

Every touched weight keeps its exact captured original signature. Restore only occurs
while the current value still matches the filtered state owned by this mod; a later
third-party change is not overwritten.

## Installation

Copy `NoDuplicateCosmetics.sdkmod` unchanged into the game's `sdk_mods` directory and
enable it in the Mod Menu.

## Test status

The underlying world-pool, ownership, leaf exclusion, exhausted-pool propagation, and
attribute-backed exclusion mechanics were validated with bounded runtime probes.
This 0.1.2 package is the first release-shaped integration candidate and still needs
ordinary gameplay validation before public release.

## Candidate diagnostics

This validation candidate emits only three normal informational lines:
`LOADED` on module import, `ENABLED` when the package is enabled, and one `READY`
verdict after the first successful ownership/filter reconcile. Periodic refreshes
remain silent unless an error occurs.

The three states are intentionally distinguishable:
- no `LOADED`: the `.sdkmod` was not discovered/imported;
- `LOADED` but no `ENABLED`: the mod exists but is disabled;
- `LOADED` + `ENABLED` + `READY`: the production filter initialized successfully.
