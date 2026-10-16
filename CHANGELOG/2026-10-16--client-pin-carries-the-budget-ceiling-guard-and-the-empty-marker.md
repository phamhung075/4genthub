## Changed

- `agenthub_client` pin moves `484bf8e` -> `9209ea1`.

### Fixed

- A seat cannot raise its own budget ceiling through the limits verb: the seat guard now refuses it (`d964b8b`).
- A set-but-empty or whitespace-only seat marker is still a seat for the limits verb (`8b8cbaa`, `9209ea1`).

Validated: `cargo test --offline` in `agenthub_client/rust/agenthub-runtime` (133 + 12 + 1 passed at `d964b8b`).
