## The 7.8 obligatory table is eight rows, cites symbols, and says what exists

### Changed

- `ai_docs/core-architecture/rigd-boundaries.md` §7.8: the obligatory table now lists **eight** rows in
  start order with `worktrees` between `gate` and `seats`, matching `seat-worktrees.md`'s own ruling
  (`daemon`, `gate`, `worktrees`, `seats`, then the four child rows) and the start-order sentence in §2.
- The same section cites functions and verbs instead of line numbers: `ensureDaemon`,
  `(*restorer).daemonUp`, `up`'s `ensureRig`, `clientlifecycle.PeakGate`, and the `clientrestore`
  package's ported-pair comment. No `*.go:NNN` citation remains in §7.8.
- One sentence now names what exists today (measured 2026-10-17 in `agenthub_client`):
  `clientservices.Safeguards()` is built and its only caller is its own test; `Verify`, `AllRunning`,
  `NotRunning` and `StateLine` are built and consumed by `doctor`, `up`'s `waitSafeguards`, agent's
  `pass()` (which calls `Verify` and reports and persists the rows; `reconcile` itself reads no row)
  and `heal`'s row read; the `Obligatory` table and its `daemon`, `gate`, `worktrees` and `seats` rows
  are NOT built; §4's `continue` deletion has NOT happened (`internal/clientrestore/continue.go` still
  registers the verb).

### Testing

Docs only; this entry and the document ride a CARRIER commit (`scripts/git-hooks/docs-only-guard`
refuses a commit whose files are all documentation, and `OWNER_DOCS_COMMIT` is the owner's alone) -
the carrier is the rule-64/wrapper change landed with it, whose message names both tasks.
Verification: a grep inside §7.8 for `\.go:[0-9]` returns nothing, the table carries eight
`| \`row\` |` lines in start order with `worktrees` third, and
`internal/clientrestore/continue.go` is still in the tree (so the "has NOT happened" sentence is true
at this commit).
