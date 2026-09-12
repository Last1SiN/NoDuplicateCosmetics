# Next bounded front

The first production-shaped stock-world implementation is now live and its startup/reconcile path has passed in-game.

## Candidate under test

`NoDuplicateCosmetics` version `0.1.2` filters only the stock world-cosmetic graph rooted at `ItemPool_SkinsAndMisc`.

Confirmed production runtime state from the first clean run:

- package imported and enabled successfully;
- graph traversal resolved **20 pools / 139 cosmetic leaves**;
- ownership mapping resolved **139/139** leaves;
- the active profile had **1 owned reachable world cosmetic**;
- production reconcile filtered exactly **1 owned leaf**;
- `exhausted_edges=0` for this profile;
- `blocked=0` and no production error was logged.

Full evidence: `research/results/production-world-filter-0.1.2.md`.

## Current validation boundary: observation-only stock-pool runner

Do not add spawning or diagnostic mutation back into the production candidate.

Build a separate development-only validator which runs alongside `NoDuplicateCosmetics 0.1.2` and does **not** mutate any loot weight, Quantity, PoolProbability, ownership/profile state, or production-mod state.

The validator should automatically:

1. wait for a stable local player and for the production filter to have already applied;
2. traverse/read the live stock world-cosmetic graph and ownership mappings;
3. confirm that every currently-owned reachable leaf is already in a disabled/excluded live weight state;
4. select the containing dedicated pool of an owned leaf and sample it, verifying `owned_hits=0` while unowned siblings still resolve;
5. sample the stock `ItemPool_SkinsAndMisc` root with a sufficiently large batch, recording observed cosmetic ratio, owned hits, unresolved hits, and category diversity;
6. require `owned_hits=0` and `unresolved=0`; record the world observed/no-drop ratio without forcing a cosmetic on every request;
7. remain read-only with respect to loot weights and restore nothing, because the validator owns no mutation;
8. emit one final PASS/REJECT verdict and otherwise avoid manual commands/keybinds.

This validates the production integration rather than re-testing the old mutation primitives.

## Still pending after this validation

- same-session acquisition refresh using a real newly-learned world cosmetic;
- disable/restore gameplay validation of the production candidate;
- generic discovery of mission/dedicated/container/DLC cosmetic sources;
- multiplayer authority/client behavior;
- compatibility arbitration for another mod changing a managed weight after `NoDuplicateCosmetics`.

Only after the observation runner passes should the front broaden beyond the stock world root.
