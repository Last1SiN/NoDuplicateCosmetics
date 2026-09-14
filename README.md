# NoDuplicateCosmetics

NoDuplicateCosmetics is a Borderlands 3 PythonSDK mod which filters already-owned cosmetics out of supported, currently loaded loot graphs **before native loot selection**, while preserving each source's original reachability and selection structure.

## Release

Current single-player release: **0.2.3**.

Validated scope is **single-player / local-player use**. Co-op has not been validated and remains `Unknown`.

## Core behavior

- owned supported cosmetics become ineligible before native selection;
- non-cosmetic entries are not replaced or reweighted;
- mixed pools continue through the game's native resolver using the remaining source-local entries;
- exhausted cosmetic-only child pools propagate exhaustion only through the exact parent edge;
- unsupported/unmapped cases fail open locally;
- same-session unlocks are refreshed without restarting;
- late-loaded sources are discovered event-driven, including a last-chance `SpawnLootAsync` / `SpawnLoot` PRE boundary;
- there is no recurring one-second/five-second full graph scan;
- guarded restore avoids overwriting a later third-party mutation of the same managed weight.

The mod does **not** write pool `Quantity`, source `PoolProbability`, source selection counts, mission state, pickup state, or profile ownership. It does not call the game's loot-spawn functions itself.

## Runtime validation

0.2.3 passed:

- representative dedicated, nested, mixed and world-drop topology tests;
- late-loaded `SpawnLootAsync` source recovery before native resolution;
- Graveward structural validation with all 139 reachable cosmetics owned and filtered while normal/dedicated non-cosmetic loot remained reachable;
- real same-session cosmetic unlock refresh;
- disable -> exact restore -> re-enable/refilter;
- external weight-conflict arbitration and guarded restore;
- final production-only Graveward smoke: **15 kills, 0 cosmetics, normal gear yes, dedicated loot yes, no periodic stutter observed**. The loop ended because Commander stopped producing further Graveward respawns.

## Installation

Place the canonical `NoDuplicateCosmetics.sdkmod` file directly in your BL3 `sdk_mods` directory and restart the game. Do not rename the `.sdkmod`: Oak requires the archive filename stem to match its single root folder name. If an extracted `sdk_mods/NoDuplicateCosmetics/` folder also exists, remove or update it because an extracted folder shadows the same-named `.sdkmod`.

## Credits

Creator / implementation: Sol (ChatGPT, GPT-5.6 Sol)  
Testing, QA and maintenance: Last1SiN

See `NoDuplicateCosmetics/README_EN.md` and `NoDuplicateCosmetics/README_RU.md` for implementation details.
