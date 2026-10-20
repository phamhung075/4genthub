The login names the token endpoint's refusal

`AuthController.Login` answered every Keycloak refusal with the same "Invalid credentials" and never
read the body. Measured 2026-10-19: two concurrent sign-ins for one valid account answered 1x200 and
1x401 "Invalid credentials" (3/3 rounds, sequential 25/25), and the 401 carried nothing that could say
why - the token endpoint's `error_description` was discarded.

The refusal body is now read once (capped at 4 KiB), its `error`/`error_description` pair is logged
without the password, and the detail names the cause:

- `error_description` naming a temporary state ("temporarily", "locked") -> 403 "Account is
  temporarily locked after repeated failed sign-ins. Try again later."
- a permanent disable -> 403 "Account is disabled. Contact an administrator."
- `invalid_grant` -> 401 "Invalid email or password. Please check your credentials and try again."
- a plain 401 with Keycloak's canonical description ("Invalid user credentials") -> 401 "Invalid
  credentials", the measured string, unchanged.
- "not fully set up" keeps its 400 registration hint; any other description now reaches the detail as
  "Authentication failed: <description>" instead of being dropped; an empty body invents no reason.

Status codes: the two named account states answer 403, not 401, because the credentials were not the
problem. Every other refusal keeps the status and detail it had.

Server log, one line per refusal:
`auth: keycloak token exchange for <email> answered <status>: error="..." description="..."`

Assumption: the matched descriptions are Keycloak's own (`Account disabled`, `Account temporarily
disabled`); the mapping was proven against a scripted token endpoint, not a live realm.
