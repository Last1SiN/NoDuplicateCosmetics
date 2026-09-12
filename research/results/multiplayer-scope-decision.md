# Multiplayer scope decision

Status: **OUT OF SCOPE FOR THIS RELEASE**

The project owner explicitly does not require co-op support for the current NoDuplicateCosmetics release.

Consequences:

- multiplayer authority/client validation is not a release blocker;
- no co-op behavior is claimed as supported;
- `coop_support` remains `Unknown` because the real two-peer matrix was not executed;
- documentation must describe the validated scope as single-player/local-player only and must not imply host/client compatibility;
- a future release may reopen multiplayer validation if co-op support becomes a requirement.

This is a product-scope decision, not evidence that co-op is incompatible.
