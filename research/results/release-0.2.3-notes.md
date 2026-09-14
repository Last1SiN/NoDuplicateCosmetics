# 0.2.3 release notes

- Event-driven late-source discovery replaces periodic full graph polling.
- Same-session unlock refresh is driven by native ownership RPCs.
- `SpawnLootAsync` and `SpawnLoot` PRE hooks provide last-chance unknown-source recovery without the mod calling either spawn function itself.
- Guarded restore preserves third-party weight mutations.
- Single-player/local-player scope validated; co-op remains unvalidated.
