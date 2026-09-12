# NoDuplicateCosmetics 0.2.0 Candidate

Generic loaded-pool production candidate for Borderlands 3.

## Current scope

0.2.0 generalizes the already validated stock-world filter. Instead of being rooted
only at `ItemPool_SkinsAndMisc`, it periodically discovers currently loaded
`ItemPoolData` assets and filters supported owned cosmetic leaves in their existing
graphs.

This is still a validation candidate, not yet a public all-source release claim.

## Behavior

- Already-owned supported cosmetic leaves become ineligible before native selection.
- Direct non-cosmetic entries are never changed.
- No entries are added and no pool is redirected to another pool.
- Child-pool exhaustion propagates upward only when the child is cosmetic-only,
  has no remaining result, and was exhausted at least partly by this mod.
- Unknown/unloaded child graphs remain reachable.
- Unmapped cosmetics and unsupported weight shapes fail open locally: their vanilla
  eligibility remains untouched instead of rejecting unrelated pools.
- Newly loaded maps/DLC pools are discovered periodically.
- Ownership is re-queried every second so newly learned mapped cosmetics can become
  ineligible without a game restart.

## Weight transforms

Only the two runtime-proven `FAttributeInitializationData` forms are mutated:

- simple constant: `BaseValueConstant -> 0`;
- attribute-backed with no DataTable/AttributeInitializer:
  `BaseValueConstant -> 0` and `BaseValueScale -> 0`.

`BaseValueAttribute` and all other fields are preserved.

## Safety / compatibility

The mod never writes pool `Quantity`, source `PoolProbability`, source selection count,
loot-attachment probability, mission state, pickup state, or profile ownership.

Every managed weight stores its exact captured original and filtered signatures.
Restore happens only while the live value still matches this mod's filtered state.
A later third-party change is left untouched and that entry becomes blocked from further
management for the session.

## Test status

Stock-world selection semantics already passed independently. 0.2.0 now requires
representative runtime validation of:

- a dedicated mission cosmetic pool;
- a nested slot-machine cosmetic pool;
- a mixed chest pool;
- the stock-world pool as a regression control.

Co-op support remains Unknown.
