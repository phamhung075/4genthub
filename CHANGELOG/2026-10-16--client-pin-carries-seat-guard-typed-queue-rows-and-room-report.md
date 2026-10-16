# Client pin carries the seat guard, typed queue rows and `room report`

### Added

- `agenthub_client` pin moves to `3834206`:
  - `seat-guard.ts` refuses hook bypass, destructive git, process kill by pattern, and writes outside the seat's
    worktree or to frozen plan paths (`b966a00`); the supervisor exports `AGENTHUB_WORKTREE`.
  - Queue rows are typed (`fc45e31`): priority `low|normal|high`, `high` needs `prod-break`, summary <=120 and
    body <=600 chars, a fixed tag set, and a repeated identical `list` within 5 minutes is refused.
  - `4genteam room report ROOM [--since 24h] [--json]` (`d33b524`, `3834206`): cost by activity, commits,
    docs-only share, queue figures and stale tasks against the five targets.

### Changed

- The unused Rust `PolicyEngine` is deleted (`eddd121`).
- Takes effect for a seat only after a client build and a reseat.

### Testing

- Client: `cargo test --offline` 125 unit + 5 guard + 1 umask passed; `go vet ./... && go test ./...` clean.
- Test changes are recorded in `TEST-CHANGELOG.md` (2026-10-16 entry).
