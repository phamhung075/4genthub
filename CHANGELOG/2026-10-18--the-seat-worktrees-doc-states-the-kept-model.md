## The seat-worktrees ruling states the landed worktree model

### Changed

- `ai_docs/core-architecture/seat-worktrees.md` now matches the client's landed derivation (`f8989ba`, on
  client `main`): `.claude` is not a submodule and is never linked; an existing registered worktree is
  **kept** - read, not re-derived - whatever branch it holds; a missing path attaches to a branch that
  already exists with no holder instead of refusing it; the registered test in `Check` is "in
  `git worktree list`, whatever branch it holds, with the `agenthub_client` link present"; the test table
  says kept, not refused.

### Measured

- `.gitmodules` records `claude-automation` and `agenthub_client`; `git rev-parse HEAD:.claude` answers
  `fatal: path '.claude' exists on disk, but not in 'HEAD'`.
- The live room on 2026-10-18: fe-dev's worktree on `fe-dashboard-update-depth`, the architect's on
  `g3-drop-classification`, the reviewer detached; only go-dev and the reviewer hold the client link, and
  go-dev holds an empty `.claude` directory with no `.git` under it.
- Client `main` was `7034a80`; the amendment was held until `f8989ba` (whose parent is `7034a80`) reached
  it, then written.

### Testing

No test: documentation. The amended passages and the test-table row were checked against the client's own
tests at `f8989ba` (kept on another branch, attach to an existing unheld branch, `.claude` never
attempted, a missing client link is wrong).
