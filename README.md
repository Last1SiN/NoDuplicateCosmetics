# NoDuplicateCosmetics

[English](README.md) | [Русский](README_RU.md)

NoDuplicateCosmetics is a Borderlands 3 PythonSDK mod which prevents already-owned cosmetics from being selected again while preserving the game's native, source-local loot behavior.

Instead of replacing a rejected cosmetic with unrelated loot, the mod makes owned cosmetic entries ineligible **before native loot selection** and leaves the original pool structure, reachability, probabilities and selection counts intact.

## Features

- Filters already-owned cosmetics before loot selection on drop.
- Preserves each source's native, source-local loot graph and reachability.
- Mixed gear + cosmetic pools continue through the game's native resolver.
- An exhausted dedicated cosmetic branch produces no cosmetic from that branch.

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

- The mod does not replace filtered cosmetics with unrelated loot.
- Pool structure, source-local reachability, probabilities and selection counts remain unchanged.
- Co-op support: **Unknown** — co-op behavior has not yet been validated.
- License: **GNU GPLv3 with [Section 7 additional provenance terms](https://github.com/Last1SiN/TrueFastball/blob/main/ADDITIONAL_TERMS.md)**

## Credits

**Development:** Sol / GPT-5.6 Sol  
**Design, testing & QA:** Last1SiN

**BL3 PythonSDK / Oak Mod Manager:** created by [apple1417](https://github.com/apple1417), with contributions from the [BL-SDK](https://github.com/bl-sdk) project and contributors.
