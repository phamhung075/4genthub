## O1a's box is ticked: the execution ledger's PostgreSQL tests are run, not skipped

### Changed

- `agenthub_go/NEXT_GEN.md` — O1a is now `[x]`. Its own closing condition was "the box stays open until the
  PostgreSQL tests above are reported as run, not skipped", and they are run, measured at HEAD:
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test ./fastmcp/task_management/...
  ./fastmcp/server/httpapp/... ./fastmcp/server/routes/... -run TaskEvent -count=1 -v` → **8 passed, 0 failed,
  0 skipped**, including `TestTaskEventAppendAssignsGaplessSeq` (0.63s) and `TestTaskEventAppendRefusesBogusKind`
  (0.85s) against a real throwaway cluster (`agenthub_go/tools/testpg/start.sh`, port 55432).
- The verdict inside the box names its artefacts by commit and `file:line` rather than by prose: the entity and
  repository `1d6c09d4`, the hand-written table `0c8122a9`, the one writer API `1c11b73c`, the read path
  `bc6349ac`, with the route measured at `server/httpapp/task_routes.go:103` — the 2026-10-08 note said `:107`,
  so the line number is corrected at this revision instead of relayed.
- **The measurement was falsified before it was trusted.** With the DSN unset the same two tests print
  `--- SKIP … SKIPPED, NOT PASSED`, so the PASS above is a run rather than a skip. The "failing first" half is
  go-dev's own record (`d554041b`, the 42P08 red of the gapless test), attributed in the box as such.
- **No Go source, test or route is touched by this commit.** O1b's box is untouched, and the pin-conditional
  lines at `NEXT_GEN.md:240-241` and `README.md:137,:149` are untouched — the held edit inside `NEXT_GEN.md` is
  deliberately NOT in this commit, which is why the commit was built from a temporary index against HEAD
  instead of committing the working-tree path.
