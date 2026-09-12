# Next bounded front

The generalized loaded-pool selection boundary, same-session real ownership refresh, normal disable/restore lifecycle, and external-conflict compatibility arbitration are now closed for the exercised cases.

Evidence:

- `research/results/generic-topology-validator-0.2.1-pass.md`
- `research/results/same-session-unlock-refresh-0.3.1-pass.md`
- `research/results/disable-restore-0.4.0-pass.md`
- `research/results/compatibility-arbitration-0.5.0-pass.md`

Confirmed with `NoDuplicateCosmetics 0.2.0`:

- representative dedicated, nested, mixed, and stock-world source-local selection semantics passed;
- a real cosmetic was learned in-session and the exact leaf was filtered without restart;
- ordinary disable restored a managed leaf to an operational positive weight and re-enable filtered it again;
- a deliberate later external weight change was not overwritten while production remained enabled;
- guarded restore preserved the conflicting external value;
- on a subsequent clean enable production adopted that external value as the new baseline, filtered it, and later restored the same external baseline;
- cleanup returned the exercised target to the vanilla baseline beneath the production filter;
- production was left enabled after each validator front.

## Current bounded front: multiplayer authority / client behavior

`coop_support` remains `Unknown` until this boundary is exercised with a **real second peer**. A single local process cannot establish whether loot-pool mutation, ownership lookup, and native loot resolution behave correctly across host/client authority boundaries.

Required minimum matrix uses two actual game peers in the same session:

1. **Host runs production; client does not.**
   - identify which peer is authoritative for the exercised loot source;
   - confirm host-owned cosmetics are filtered from host-instanced loot;
   - determine what a client with different ownership receives;
   - require no crash/desync and no mutation of client profile ownership.
2. **Both peers run production.**
   - use profiles with intentionally different ownership for at least one reachable cosmetic;
   - confirm each peer's instanced loot follows that peer's ownership where the game exposes per-player instancing;
   - detect whether both Python processes touch the same authoritative pool object or only their local copies;
   - require no cross-peer overwrite/oscillation of managed weights.
3. **Client runs production; host does not.**
   - establish whether client-side pool mutation has any effect on authoritative loot generation;
   - if it does not, record the mod as host-required rather than pretending client-only support.

Preferred first source is a simple one-item dedicated cosmetic pool plus the already validated world root as a no-drop regression control. Do not start with mixed chest or mission-completion side effects.

Instrumentation should be observation-first and log at minimum:

- network role / authority indicators for local player and spawned pickup where available;
- local profile ownership for the exercised balance;
- target weight signature before/after production filtering on each peer;
- whether the exact target resolves for each peer;
- loot instancing/owner-controller fields when observable;
- peer role (`host` / `client`) and whether production is enabled on that peer.

Do not infer co-op support from single-player success. Do not change `coop_support = "Unknown"` until the real two-peer matrix supports a narrower claim.

## Boundary after multiplayer validation

If the two-peer matrix passes, classify the actual co-op support mode (`HostOnly`, `RequiresAllPlayers`, `ClientSide`, or another evidence-backed description), then perform release cleanup:

1. remove validation-only INFO diagnostics from production;
2. fix README candidate wording and finalize public documentation;
3. bump to the release version with numeric dotted metadata only;
4. build canonical `.sdkmod` and Nexus outer ZIP;
5. run final archive/compile/metadata/safety verification.
