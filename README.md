# NoDuplicateCosmetics

[English](README.md) | [Русский](README_RU.md)

NoDuplicateCosmetics stops cosmetics you already own from dropping again.

It does not turn a blocked cosmetic into bonus gear or reroll the drop into something unrelated. The owned cosmetic is simply removed from the choices before Borderlands 3 picks the drop, so the rest of that loot source keeps behaving normally.

## Features

- Prevents already-owned cosmetics from dropping again.
- Works before the game makes its final loot choice.
- Does not replace blocked cosmetics with unrelated items.
- Mixed loot pools still behave normally.
- If a cosmetic-only branch has nothing new left to give you, that branch simply gives no cosmetic.

## Requirements

- Borderlands 3
- [BL3 PythonSDK / Oak Mod Manager](https://github.com/bl-sdk/oak-mod-manager/releases/latest)

Use the [official BL3 SDK / Oak installation guide](https://bl-sdk.github.io/oak-mod-db/) for SDK installation and updates.

## Installing the mod

1. Install or update BL3 PythonSDK / Oak using the official guide above.
2. Download `NoDuplicateCosmetics.sdkmod` from [GitHub Releases](https://github.com/Last1SiN/NoDuplicateCosmetics/releases/latest).
3. With Borderlands 3 closed, copy the `.sdkmod` file intact to `Borderlands 3\sdk_mods\`. Do not extract the `.sdkmod` itself.
4. Remove old NoDuplicateCosmetics test/probe builds so only one NoDuplicateCosmetics runtime mod can load.
5. Start the game, open **MODS -> NoDuplicateCosmetics** and enable the mod.

To update NoDuplicateCosmetics, replace the existing `.sdkmod` with the newer file and restart the game.

## Compatibility and license

- The mod does not replace filtered cosmetics with unrelated loot.
- Pool structure, source-local reachability, probabilities and selection counts remain unchanged.
- Co-op support: **Unknown** — co-op behavior has not yet been validated.
- License: **GNU GPLv3 with [Section 7 additional provenance terms](ADDITIONAL_TERMS.md)**

## Credits

**Development:** Sol / GPT-5.6 Sol  
**Design, testing & QA:** Last1SiN

**BL3 PythonSDK / Oak Mod Manager:** created by [apple1417](https://github.com/apple1417), with contributions from the [BL-SDK](https://github.com/bl-sdk) project and contributors.
