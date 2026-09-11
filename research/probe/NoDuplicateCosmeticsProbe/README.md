# NoDuplicateCosmeticsProbe 0.7.1

Fully automatic attribute-backed-weight probe.

Enable the mod before loading into a character. No commands or keybinds are required.

After the local player and pawn remain valid for two seconds, the probe automatically:

1. discovers a direct attribute-backed stock ECHO leaf, preferring a Common rarity-weight leaf so the test gets many target samples with only 256 requests;
2. runs a 256-request baseline;
3. sets only `BaseValueConstant=0`, runs 256 requests, then restores exactly;
4. sets `BaseValueConstant=0` and `BaseValueScale=0`, runs 256 requests, then restores exactly;
5. verifies the captured signature and emits one `AUTO_VERDICT` line.

The probe waits for each 256-result batch to complete instead of relying on manual delays. Each batch has a 15-second fail-closed timeout.

No profile ownership, Quantity, PoolProbability, parent pool, or sibling weight is changed.

Send `unrealsdk.log` after `AUTO_VERDICT` appears.
