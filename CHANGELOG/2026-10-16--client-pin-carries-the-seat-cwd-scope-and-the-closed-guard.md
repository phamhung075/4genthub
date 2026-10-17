## Client pin carries the seat start directory and the closed worktree-scope guard

### Changed
- `agenthub_client` pin `5aeb223` -> `484bf8e`: a seat starts in the directory the room names for it (`f1d5396`) and the guard's `worktree-scope` roots at `AGENTHUB_WORKTREES` and no longer fails open when the variable is unset (`484bf8e`).
- The room `4genthub-min` `spec.json` now names a `cwd` for each of the five seats (the lead in the main checkout, the others in their own worktrees); the top-level `cwd` stays null.

### Testing
- `cargo test --offline` in `rust/agenthub-runtime`: 133 unit + 11 `seat_guard` + 1, 0 failed.
