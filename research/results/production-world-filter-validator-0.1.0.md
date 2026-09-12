# Production stock-world filter validator 0.1.0

Verdict: **PASS**.

Runtime evidence from `unrealsdk(20260912-074748).log` validates the release-shaped `NoDuplicateCosmetics 0.1.2` stock-world filter under an independent read-only validator.

Observed facts:

- production candidate loaded and enabled cleanly;
- production READY: `20 pools / 139 leaves / 139 mapped / 1 owned / 1 filtered leaf / 0 exhausted edges / 0 blocked`;
- validator precheck confirmed every currently-owned reachable stock-world cosmetic leaf was already in a disabled/excluded live state before sampling;
- direct containing Siren-head pool: `128/128` cosmetic results, `owned_hits=0`, `unresolved=0`, `distinct=5`;
- unowned siblings continued to resolve normally from that same source-local pool;
- world root `ItemPool_SkinsAndMisc`: `512` requests -> `235` cosmetic observations (`0.4590`), `owned_hits=0`, `unresolved=0`, `distinct=63`;
- all three runtime ownership classes appeared in the world sample: `OakCustomizationData`, `OakInventoryCustomizationPartData`, and `CrewQuartersDecorationItemData`;
- world root did **not** become a guaranteed cosmetic drop: native no-drop behavior remained present;
- validator owned no mutation (`mutation_by_validator=NO`).

Final runtime verdict:

```text
[NDCValidator] AUTO_VERDICT PASS owned_reachable=1 direct_owned_hits=0 world_owned_hits=0 world_ratio=0.4590 world_distinct=63 native_no_drop_present=YES mutation_by_validator=NO
```

This closes the primary stock-world production behavior boundary: owned reachable cosmetics are excluded before selection, unowned source-local siblings still resolve, and native world-root no-drop semantics remain intact.

Still separate lifecycle/coverage work:

- same-session unlock refresh after learning a new cosmetic;
- disable / guarded-restore validation;
- non-world source discovery (mission rewards, dedicated enemy pools, lootables/containers, DLC/event-specific sources);
- multiplayer authority/client behavior;
- compatibility arbitration when another mod changes a managed weight after filtering.
