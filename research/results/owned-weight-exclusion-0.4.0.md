# Owned-weight exclusion probe 0.4.0 — runtime verdict

Status: **PASS**

## Scope

Bounded mutation of exactly one stock cosmetic leaf entry:

- pool: `/Game/Pickups/Customizations/_Design/ItemPools/Heads/ItemPool_Customizations_Heads_Loot_Siren.ItemPool_Customizations_Heads_Loot_Siren`
- balance: `/Game/PlayerCharacters/_Customizations/SirenBrawler/Heads/CustomHead_Siren_4.InvBal_CustomHead_Siren_4`
- display name: `Motosaurus`
- mutation: `Weight.BaseValueConstant 1.0 -> 0.0`

No `Quantity`, parent `PoolProbability`, sibling entry, profile, or unrelated pool was modified.

## Runtime evidence

The live Siren head pool contained six entries. Motosaurus was found at index 1 with a simple constant weight signature:

`BaseValueConstant=1.0, DataTable=None, BaseValueAttribute=None, AttributeInitializer=None, BaseValueScale=1.0`

The local profile reported Motosaurus as owned once the player/profile state was ready.

### Baseline

96 requests against the exact Siren head pool:

- observed: 96
- Motosaurus hits: 12
- distinct results: 6

Counts:

- Starry Eyed: 20
- Chokella: 18
- Bird Collar: 17
- Mane Event: 16
- Cry Havoc: 13
- Motosaurus: 12

### Filtered

After setting only Motosaurus `Weight.BaseValueConstant` to `0.0`:

96 requests:

- observed: 96
- Motosaurus hits: 0
- distinct results: 5

Counts:

- Mane Event: 23
- Starry Eyed: 21
- Bird Collar: 18
- Chokella: 17
- Cry Havoc: 17

This is the key result: removing one positive-weight cosmetic did **not** create a corresponding no-drop slot. All 96 requests still produced results, and the remaining positive entries absorbed the selection probability. For this stock `ItemPoolData` leaf, zeroing an entry weight has the required source-local reroll semantics.

### Restore

The probe restored the exact captured weight signature and logged:

`RESTORE PASS exact weight signature restored`

A second 96-request run after restore produced:

- observed: 96
- Motosaurus hits: 12
- distinct results: 6

Manual verification also showed the original `BaseValueConstant=1.0` signature.

## Startup timing finding

At module enable, the same session initially returned `Motosaurus is not owned on this profile`. Roughly 100 seconds later, after normal game/player state became available, the exact same ownership query returned `owned=YES` and remained stable through the experiment.

Therefore production code must **not** permanently decide ownership during early module enable. Ownership filtering must be delayed/lazy and refreshed only when a usable local player/profile state exists. The most likely cause is profile/player readiness timing, but the runtime fact we rely on is simply that the early query is not authoritative.

## Consequence

The fundamental leaf-filter mechanism is validated:

- pre-selection exclusion by zeroing the owned leaf's weight works;
- the remaining positive entries are selected normally;
- exact restoration is possible with an ownership guard;
- no post-spawn deletion/reroll is needed for this class of pool.

Next bounded front: apply the same ownership-driven filtering recursively across the stock world-cosmetic graph, while leaving every source `Quantity` and parent probability unchanged and preserving exact restore ownership for every touched entry.