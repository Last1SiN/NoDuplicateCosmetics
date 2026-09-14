# Release scope

Current release target: single-player/local-player behavior only.

Validated boundaries:

- generalized loaded-pool source-local filtering across representative dedicated, nested, mixed, and stock-world topologies;
- native world-root no-drop preservation;
- same-session real cosmetic unlock refresh without restart;
- normal disable/restore/re-enable lifecycle;
- guarded restore and external-conflict compatibility arbitration.

Not validated / not claimed:

- multiplayer host/client authority behavior;
- co-op ownership semantics across peers.

Metadata remains `coop_support = "Unknown"` until a future real two-peer validation front is completed.
