# The SQLite paths and the marker-less root resolver are gone

Date: 2026-10-18. Hub task `a47e0da5` (G2 residual), queue row `qitem-20261017221351-2861856dde90`.

## What the tree held at `ae674916`

- `agenthub_go/fastmcp/task_management/infrastructure/database/database_source_manager.go` — the
  legacy SQLite path manager ported from `database_source_manager.py`: 254 lines, a mode enum built on
  `/data/agenthub.db` and `agenthub_test.db`, an `MCP_DB_PATH`/`DOCKER_DB_PATH` branch, a lazy global
  and four module-level wrappers. **Zero non-test callers** (`grep -rn` over `agenthub_go` for
  `NewDatabaseSourceManager|DatabaseSourceManagerInstance|GetDatabasePath|GetDatabaseMode|
  GetDatabaseInfo|ClearDatabaseSourceManagerInstance` outside the file itself: nothing), and `go.mod`
  has no SQLite driver, so every path in it was unreachable by construction.
- `SubtaskRepositoryFactory.CreateSQLiteSubtaskRepository` (delegating to the ORM) and
  `GetSubtaskDBPath` (`MCP_DB_PATH`, else `<ProjectRoot>/data/agenthub.db`) — same measurement, no
  non-test callers.
- `unified_logging.go:GetProjectRoot` — the FIFTH project-root resolver and the only one that
  consulted no marker: `/app` when that directory exists, otherwise a FIXED FIVE-LEVEL walk from
  `os.Executable()` under a comment naming the removed Python tree's depth.

## What changed

- Both files' SQLite halves are deleted: the whole `database_source_manager.go` and its
  `database_source_manager_test.go`, and the two factory methods. `subtask_repository_factory.go`
  keeps `CreateSubtaskRepository` (the live path) and its `AGENTHUB_DATA_PATH` usage.
- `GetProjectRoot` now answers `utilities.DefaultEnv().FindProjectRoot()` — the SAME marker every
  other root site uses (a directory holding `agenthub_go`, then `AGENTHUB_DATA_PATH`, then
  `/tmp/agenthub_project`). The dead `dirOf` helper went with the walk.

## Measured, from a built binary (`go build -o /tmp/g5-root`, a program printing `GetProjectRoot()`)

- run from `/tmp`: `/tmp/agenthub_project` (was: the old formula's five-level walk from
  `/tmp/g5-root` computes `/`, which is where it would have written `logs/`).
- run from the repository root: `/home/daihu/.config/4genthub/rooms/4genthub-min/wt/go-dev-root`.

## Checks

- `gofmt -l` over the touched packages: clean (the only hit is the throwaway measurement module, not
  part of the change).
- `go build ./...`: clean.
- `go vet ./fastmcp/task_management/infrastructure/... ./fastmcp/task_management/infrastructure/repositories/`:
  clean.
- `go test ./fastmcp/task_management/infrastructure/... ./fastmcp/task_management/infrastructure/repositories/ -count=1`:
  all packages ok (18 packages, 0 failures).

## The clause, ruled

G2's plan clause "do not re-key them on another directory" is recorded as **SUPERSEDED** beside the
clause itself in `ai_docs/core-architecture/agenthub-system-architecture.md` (the G2 gap bullet), with
the ruling's reason: the guarded failure is a root finder depending on a directory that can be ABSENT,
which the removed Python tree was and `agenthub_go` cannot be. The same file's AT HEAD block carried
three citations of the now-deleted `database_source_manager.go`; they are corrected in place with the
date and the reason, so the page does not cite a file that no longer exists.
