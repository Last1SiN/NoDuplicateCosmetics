# Release cleanup plan

Branch from the latest validated single-player research state and produce the public release without changing the proven filtering architecture.

Required cleanup:

- remove validation-only normal INFO diagnostics from production;
- preserve error-only operational logging;
- remove candidate wording from public docs;
- state single-player/local-player validated scope and keep co-op `Unknown`;
- retain numeric dotted versioning;
- verify no production `SpawnLootAsync`, command/keybind, profile mutation, `Quantity`, or `PoolProbability` writes;
- build canonical sdkmod and Nexus outer ZIP;
- reopen and verify archives, compile, metadata, docs, and hashes.
