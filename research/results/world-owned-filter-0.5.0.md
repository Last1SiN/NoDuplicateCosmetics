# Recursive stock-world owned filter — probe 0.5.0

Verdict: **PASS for the tested stock world graph and currently-owned leaves**.

Runtime log: `unrealsdk(20260911-141440).log`.

## Graph

The probe recursively resolved the vanilla graph rooted at `ItemPool_SkinsAndMisc`:

- 20 reachable pools
- 139 direct cosmetic leaf entries
- 16 pools containing direct cosmetic leaves
- no unresolved cosmetic drops in the measured batches

The graph included all six stock world branches: heads, skins, weapon skins, weapon trinkets, ECHO themes, and room decorations, including character-specific head/skin children and rarity-specific room-decoration children.

## Ownership plan

The local profile had exactly one owned cosmetic among the 139 stock-world leaves at test time:

- Siren head `Motosaurus`
- pool: `ItemPool_Customizations_Heads_Loot_Siren`
- balance: `CustomHead_Siren_4.InvBal_CustomHead_Siren_4`
- captured weight: simple constant `1.0`

Plan result:

- `owned_total=1`
- `mutation_candidates=1`
- `already_zero_owned=0`

## Runtime batches

Baseline world batch:

- requests: 384
- observed cosmetics: 153
- observed ratio: 0.3984
- owned hits: 1 (`Motosaurus`)
- unresolved hits: 0

Filtered world batch after the owned leaf was zeroed:

- requests: 384
- observed cosmetics: 154
- observed ratio: 0.4010
- owned hits: 0
- unresolved hits: 0

The near-identical baseline/filtered observed ratios show that leaf exclusion did not convert the removed item weight into an additional root no-drop slot. The stock root `Quantity` behavior remained intact while the owned leaf became ineligible.

Restore:

- exact captured signatures restored: PASS
- manual verification after restore: `good=1 bad=0`

The restored batch did not happen to roll Motosaurus in 177 observed cosmetics. This is not a restore failure: exact weight verification passed, and the target is low-probability at the world-root level.

## Established facts

1. Recursive discovery from the exact stock world root is viable and preserves source-local reachability.
2. All 139 tested leaf balances were resolvable through the known customization ownership mappings.
3. Ownership-driven zero-weight exclusion works inside the real nested world graph, not only in a direct isolated pool.
4. The root's native no-drop behavior is preserved when a non-exhausting leaf is removed.
5. Exact guarded restore works across the recursive-plan implementation.

## Remaining boundary

This run had only one owned stock-world leaf, so it did not exercise pool/category exhaustion. The next bounded front must deliberately simulate exhaustion of one exact cosmetic child pool and verify both required semantics:

- a directly rolled exhausted dedicated cosmetic pool yields no replacement drop;
- when that exhausted pool is a child of a broader source which still has other eligible branches, exhaustion propagates upward so the parent rerolls among its remaining source-local branches without changing the parent's native `Quantity` behavior.
