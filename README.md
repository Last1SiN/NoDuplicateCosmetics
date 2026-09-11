# NoDuplicateCosmetics

Research and implementation repository for a Borderlands 3 SDK mod which prevents already-owned cosmetics from being selected by supported loot sources while preserving the original source-local loot graph.

## Core invariant

NoDuplicateCosmetics must preserve both the semantics and the reachability of the original loot source. It must not blindly destroy an owned cosmetic after spawn, must not globally convert cosmetic rolls into weapon rolls, and must never introduce a cosmetic which the original source could not drop.

## Current implementation front

`implementation/stock-world-filter-v0.1` contains the first production-shaped candidate, version `0.1.0`.

Current scope is deliberately limited to the vanilla world-cosmetic graph rooted at `ItemPool_SkinsAndMisc`.

The candidate:

- waits lazily for a loaded local player/profile context;
- resolves ownership through the three runtime-confirmed APIs for character/ECHO cosmetics, weapon cosmetics, and room decorations;
- filters owned simple-constant leaves with `BaseValueConstant = 0`;
- filters the runtime-confirmed attribute-backed shape with `BaseValueConstant = 0` and `BaseValueScale = 0` while preserving the attribute pointer;
- propagates exhausted child pools upward only through the same source-local graph;
- never changes source `Quantity`, `PoolProbability`, profile data, non-cosmetic entries, or foreign pools;
- refreshes ownership during the same session so newly learned cosmetics become ineligible without restarting;
- uses guarded exact restore and does not overwrite a later third-party mutation of the same weight;
- fails closed on unresolved ownership or unsupported weight shapes.

The implementation contains no development spawner, diagnostic keybinds, console commands, or normal-operation info logging.

## Still outside the current candidate

- generic coverage of every mission/dedicated/container/DLC-specific cosmetic source;
- unsupported DataTable-backed or `AttributeInitializer`-backed weight shapes;
- multiplayer authority/client validation;
- full compatibility arbitration for mods which rewrite the same loot graph after NoDuplicateCosmetics has already filtered it.

The research evidence and bounded probe results are kept under `research/`.
