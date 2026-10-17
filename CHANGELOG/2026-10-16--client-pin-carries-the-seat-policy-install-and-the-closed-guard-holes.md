## Changed

- `agenthub_client` pin moves `9209ea1` -> `e2b81cb`.

### Fixed

- The hub's seat-policy render is installed as `<seat dir>/config.yml` at launch, so the per-role `edit`/`ast_edit` deny binds the seats (`e2b81cb`).
- The seat guard no longer steps past an empty value in an env prefix, and judges the paths that create a directory entry (`769900e`).
- The park's way back is pinned on both runtime routes (`abe9028`, `2e0564f`); the criteria request shape is pinned (`11a77ca`).

Validated: `cargo test --offline` in `agenthub_client/rust/agenthub-runtime` (133 + 15 + 1 passed at `769900e`); gate PASS by the reviewer at `e2b81cb`.
