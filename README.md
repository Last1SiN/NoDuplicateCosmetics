# NoDuplicateCosmetics

[English](README.md) | [Русский](README_RU.md)

NoDuplicateCosmetics is a Borderlands 3 PythonSDK mod which prevents already-owned supported cosmetics from being selected again while preserving the game's native, source-local loot behavior.

Instead of replacing a rejected cosmetic with unrelated loot, the mod makes owned cosmetic entries ineligible **before native loot selection** and leaves the original pool structure, reachability, probabilities and selection counts intact.

## Features

- Filters already-owned supported cosmetics before native loot selection.
- Preserves each source's native, source-local loot graph and reachability.
- Does not replace a blocked cosmetic with a gun or another unrelated item.
- Mixed gear + cosmetic pools continue through the game's native resolver among the remaining eligible entries.
- An exhausted dedicated cosmetic branch produces no cosmetic from that branch.
- Nested cosmetic-only exhaustion can disable only the exact parent edge leading to the exhausted child pool.
- Refreshes ownership after a cosmetic is unlocked during the same game session.
- Detects newly loaded loot sources through event-driven hooks instead of periodic full graph polling.
- Uses guarded restore logic so a later third-party weight change is not overwritten.
- Unsupported or unresolved cosmetic/weight shapes fail open locally instead of blocking unrelated loot.
- Normal gameplay logging is limited to errors.

## Requirements

- Borderlands 3
- [BL3 PythonSDK / Oak Mod Manager](https://github.com/bl-sdk/oak-mod-manager/releases/latest)

Use the [official BL3 SDK / Oak installation guide](https://bl-sdk.github.io/oak-mod-db/) for SDK installation and updates.

## Installing the mod

1. Install or update BL3 PythonSDK / Oak using the official guide above.
2. Download `NoDuplicateCosmetics.sdkmod` from [GitHub Releases](https://github.com/Last1SiN/NoDuplicateCosmetics/releases/latest).
3. With Borderlands 3 closed, copy the `.sdkmod` file intact to `Borderlands 3\sdk_mods\`. Do not extract or rename the `.sdkmod` itself.
4. If an extracted `sdk_mods/NoDuplicateCosmetics/` folder exists, remove or update it because an extracted folder takes priority over the same-named `.sdkmod`.
5. Start the game, open **MODS -> NoDuplicateCosmetics** and enable the mod.

To update NoDuplicateCosmetics, replace the existing `.sdkmod` with the newer canonical file and restart the game.

## Compatibility and license

- Validated scope: **single-player / local-player use**.
- Co-op support: **Unknown** — co-op behavior has not yet been validated.
- The mod does not write pool `Quantity`, source `PoolProbability`, source selection counts, mission state, pickup state or profile ownership.
- Release 0.2.3 was runtime-validated against dedicated, nested, mixed and world-drop topology, late-loaded source recovery, same-session unlock refresh, disable/restore and third-party weight-conflict arbitration.
- License: **GNU GPLv3**.

## Credits

**Development:** Sol / GPT-5.6 Sol  
**Design, testing & QA:** Last1SiN

**BL3 PythonSDK / Oak Mod Manager:** created by [apple1417](https://github.com/apple1417), with contributions from the [BL-SDK](https://github.com/bl-sdk) project and contributors.
