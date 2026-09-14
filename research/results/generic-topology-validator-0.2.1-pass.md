# Generic representative topology validation — PASS

Date: 2026-09-12
Production candidate: `NoDuplicateCosmetics 0.2.0`
Validator: `NoDuplicateCosmeticsTopologyValidator 0.2.1`

## Result

PASS.

Production initialization remained clean:

- loaded pools: `717`
- cosmetic leaves: `218`
- mapped cosmetics: `218`
- unmapped cosmetics: `0`
- owned reachable cosmetics: `1`
- filtered leaves: `1`
- exhausted edges: `0`
- unsupported owned shapes: `0`
- ownership unresolved: `0`
- blocked entries: `0`
- cycles: `0`

Representative source-local cases:

### Dedicated mission cosmetic pool

Pool: `ItemPool_Customizations_WeaponTrinkets_Mission_28`

- topology: dedicated cosmetic
- reachable cosmetics: `1`
- current profile: `0` owned, `1` unowned
- 64 requests -> 64 observed
- owned hits: `0`
- unresolved: `0`
- foreign: `0`
- verdict: PASS, control-only (no owned reachable cosmetic in this source)

### Nested slot-machine cosmetic pool

Pool: `ItemPool_Customizations_Heads_SlotMachine`

- topology: nested cosmetic
- 5 pools / 24 cosmetic leaves
- current profile: `1` owned / `23` unowned
- 128 requests -> 128 cosmetics
- owned hits: `0`
- unresolved: `0`
- foreign: `0`
- 18 distinct observed cosmetics
- verdict: PASS, owned-filter-covered

### Stock world regression

Pool: `ItemPool_SkinsAndMisc`

- topology: nested cosmetic
- 20 pools / 139 cosmetic leaves
- current profile: `1` owned / `138` unowned
- 384 requests -> 175 observed cosmetics
- observed ratio: `0.4557`
- owned hits: `0`
- unresolved: `0`
- foreign: `0`
- 57 distinct observed cosmetics
- native no-drop preserved
- verdict: PASS, owned-filter-covered

### Mixed red-chest pool

Pool: `ItemPool_RedChestFlaps`

- topology: mixed cosmetic/non-cosmetic
- 65 pools / 139 cosmetic leaves / 91 non-cosmetic leaves
- current profile: `1` owned / `138` unowned cosmetics
- 192 requests -> 173 observed inventory states
- cosmetic: `18`
- non-cosmetic: `155`
- owned hits: `0`
- unresolved: `0`
- foreign: `0`
- verdict: PASS, owned-filter-covered

Final validator verdict:

`AUTO_VERDICT PASS cases=4 ... foreign_hits=0 owned_hits=0 mutation_by_validator=NO`

## Consequence

The representative topology boundary for generalized loaded-pool filtering is closed:

- dedicated cosmetic source behavior is intact;
- nested cosmetic filtering excludes owned leaves without broadening reachability;
- mixed pools retain non-cosmetic resolution while excluding owned cosmetics;
- stock-world no-drop behavior remains intact;
- no foreign results were introduced.

The next bounded front is same-session ownership refresh with a real cosmetic ownership transition while the game remains running.
