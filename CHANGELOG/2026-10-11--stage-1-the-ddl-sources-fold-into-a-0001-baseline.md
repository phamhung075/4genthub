# Stage 1: the DDL sources fold into one 0001 baseline

Stage 1 of the migration work: the schema's seven `TableDef` sets and the embedded init SQL stop being
"the schema" on their own. The runner's migration set is the schema, and the step that carries the
tables a database already has is a file.

## Why a baseline at all

`migration_runner.go` applies one file per step from `migrations/`, records the step's name in
`applied_migrations`, and skips what is already recorded. That is the only shape in which schema change
becomes auditable, and it only works if the schema a database already holds is one of the steps. So the
tables the runtime registry declares are now also in `0001_baseline.sql`: on a fresh database the step
executes and creates them; on an existing database the step must NOT execute, and the mark that records
it is an owner action (`Runner.MarkBaseline`) because deciding that a live database equals this file is
a claim about production data.

## Changed

- **`migrations/0001_baseline.sql`** (new): 41 tables with their indexes, every statement
  `IF NOT EXISTS` because `createAll` (the registry's own DDL) runs before the runner on this path. It
  was generated from the runtime registry by a throwaway command in `.gotmp` and then frozen; 0002 and
  0003 stay as they are. The six `ProductionTables` are deliberately absent - nothing appends them to
  the runtime set, so no code path creates them today, and whether a live database holds them is the
  dump comparison's question rather than this file's.
- **`schema_matches_definitions_test.go`** (new): the guard. Every table in `taskdb.Tables` must be
  created by some step of the set, compared on the four axes the seat schema had already drifted on -
  the column NAME set, the referenced-TABLE multiset, the CHECK expressions and the column DEFAULTs.
  It is an **external test package** on purpose: `taskdb.Tables` is a package-level union each feature
  package appends to in its own `init`, so the blank imports of task_management, auth, seat_management
  and rig_safeguard are what make the test see the same set `createAll` walks. Without them it would
  quietly see a fifth of the schema and pass.
- **`migrations/README.md`**: its "no `0001` file exists yet" paragraph is replaced with what the file
  now is.
- **`migration_runner_integration_test.go`**: the `MarkBaseline` case's fixture step was named
  `0001_baseline`, which was a free name until this commit and is now the real step's name. That case
  calls `newMigrationRunnerEnv`, which runs `CreateTables` - so the embedded set was already recorded,
  `MarkBaseline("0001_baseline")` marked nothing, and the case failed on `marked [], want
  [0001_baseline]`. The fixture is `0900_baseline_probe` now, a name the embedded set cannot contain,
  and the assertion is unchanged.

## Verified

- The acceptance this row turns on, both directions: the test was **shown failing first**, on every
  registered table, by perturbing a Go definition; with the baseline present the same test is green and
  so is the package.
- `gofmt -l` over `fastmcp/`: empty. `go build ./...`: rc 0. `go vet ./fastmcp/task_management/...
  ./fastmcp/server/httpapp/...`: rc 0.
- `AGENTHUB_TEST_PG_URL=… go test -count=1 ./fastmcp/task_management/infrastructure/database/` ->
  **ok 22.997s** (this is the package the fixture rename is in, and the package the baseline executes
  in).

## Not done, and why (not a gap in this commit)

- **The live-database dump comparison has not been run, and cannot be run from this box.** Measured
  now, not recalled: the only PostgreSQL reachable here is the scratch test server
  (`127.0.0.1:55995`) and it holds exactly one database, `postgres`, with no application tables and no
  `applied_migrations`; there is no dump artifact anywhere in the seat directory. So "does a live
  database hold the six `ProductionTables`, and does it hold `applied_migrations`" is still unmeasured.
  It needs the principal: a dump from the dev/production database, or a client plus reachable access.
  Committing this file changes nothing live - the comparison gates *marking* a live database, not
  writing the file, and `MarkBaseline` remains an owner action.
