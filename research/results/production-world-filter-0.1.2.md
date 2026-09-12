# Production world filter 0.1.2 runtime result

Verdict: **STARTUP / RECONCILE PASS; drop-behavior validation still required**.

Observed runtime facts from `unrealsdk(20260912-073704).log`:

- the production package was discovered and imported: `LOADED candidate=0.1.2`;
- the mod was enabled: `ENABLED candidate=0.1.2 waiting_for_player`;
- after loading a character, the first production reconcile completed successfully;
- the stock world-cosmetic graph resolved to **20 pools** and **139 cosmetic leaves**;
- ownership mapping resolved **139/139** leaves;
- the active profile had **1 owned reachable world cosmetic**;
- production filtering made exactly **1 owned leaf** ineligible;
- no child branch was exhausted in this profile (`exhausted_edges=0`);
- no compatibility/restore blockers were present (`blocked=0`);
- no `NoDuplicateCosmetics` error was emitted in the captured log.

Runtime READY line:

```text
[NoDuplicateCosmetics] READY candidate=0.1.2 pools=20 leaves=139 mapped=139 owned=1 filtered_leaves=1 exhausted_edges=0 blocked=0
```

This closes loader, player-readiness, graph traversal, ownership mapping, and first production reconcile for the stock world graph.

It does **not** by itself prove actual selection behavior from the production-filtered pool. The next bounded validation must be observation/spawn-only: leave production mutation ownership with `NoDuplicateCosmetics`, sample the already-filtered stock pools, verify zero owned hits, verify unowned siblings continue to resolve, and capture the world-root observed/no-drop ratio without adding mutation logic back into the production mod.
