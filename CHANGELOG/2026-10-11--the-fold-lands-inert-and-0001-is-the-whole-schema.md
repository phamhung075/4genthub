# The fold lands inert — 0001 is the whole schema, and a boot never applies it to a database that has one

T12's stage 1 ends with the DDL sources folded into ONE ordered set. This lands the fold's file and its
two guards. The **cutover** — deleting `createAll`, the init SQL and the ensurers, leaving the migrations
as the only schema creator — is deliberately NOT here, and neither is the ensurers' split; the runner
and its ledger landed in `2026-10-10--the-migration-runner-and-the-ledger-writer-land.md`.

## The landmine this commit is shaped around

The moment `0001_baseline.sql` lands inside `migrations/`, the boot runner already wired at
`database_config.go:470` would apply it to every unmarked database at the next boot — starting with the
live one — and fail on `CREATE TYPE` / `CREATE TABLE` for objects that already exist.

**How the fold is inert at boot:** `Runner.Apply` reads the CATALOGUE first for that one step
(`migration_runner.go`, `catalogueIsEmpty` over `engine.go`'s `tableNames`, current schema):

- catalogue **not** empty → the step is SKIPPED: no SQL, no ledger row, one log line per runner
  (`sync.Once`, so a boot's explanation is one line, not one per caller);
- catalogue **empty** → it applies normally, which is the one case the baseline is for;
- the catalogue read **fails** → the step is refused (fail closed): "cannot tell" is never read as
  "empty";
- the ledger is ensured AFTER the baseline's SQL, not before it, because the baseline is what CREATES
  `applied_migrations` — ensuring it first would collide with the step's own `CREATE TABLE`;
- every other step is unchanged, and the rule is fixed, not configurable.

This is the rule `db_initializer.go` already obeys for the init SQL: a populated catalogue never reaches
DDL that creates the schema. `Runner.MarkBaseline` remains the owner's path for RECORDING the baseline
on a database that already has the schema, and nothing here marks anything.

## What landed

- **`fastmcp/task_management/infrastructure/database/migrations/0001_baseline.sql`** — GENERATED from
  the runtime `TableDef` registry in the order `createAll` walks it: the aggregate `taskdb.Tables`
  (**41**: task_management 19, task_events, auth 2 + email_tokens, seat 15, team 2, rig_safeguards 1)
  first, then `taskdb.ProductionTables` (**6**: `agent_import_history`, `applied_migrations`,
  `token_transactions`, `user_agent_configurations_md`, `user_api_tokens`, `user_sessions`). 47
  `CREATE TABLE`, one `CREATE TYPE progressstate` emitted before the table whose columns carry it, 911
  lines (`wc -l`, and the file ends with a newline), sha256 `a3e3109230355aa93098002caf4992e4746ff63bcb1a18facebad38b6422ab29`. Plain DDL: **no**
  `DROP`, **no** `ALTER`, **no** `IF NOT EXISTS` — a faithful snapshot, not an idempotent guess.
- **The second registry is the finding that shaped the file.** `ProductionTables` is deliberately
  outside the aggregate (`models_prod.go:19-25`; three of its tables carry a `user_id` FK to `users`),
  so a generator that walks only `Tables` produces a baseline **missing six tables** — `token_transactions`,
  `user_api_tokens` and `user_sessions` among them, which today only the init SQL creates. The order is
  the dependency: the aggregate (which holds `users`) is emitted first.
- **`migration_baseline_parity_test.go`** — the parity guard the fold needs
  (`TestSchemaMatchesGoDefinitions`, the name the stage-1 acceptance gives it), because a GENERATED file
  drifts silently from the registry it came from. Per table: the column-NAME set, the `REFERENCES`
  multiset and the normalised `CHECK` expressions must agree with the `TableDef` DDL; a table in the
  file that no `TableDef` registers fails in the other direction; a table registered twice fails; an
  enum must be created before the table that uses it; and no `DROP`/`ALTER` may appear (comment lines
  excluded, so the header's prose cannot hide one). It lives in the EXTERNAL test package with the
  appending packages' blank imports, because `taskdb.Tables` is completed by `init()` in the seat, rig
  and auth packages — an internal test file would see 20 tables and hold the file to the wrong set.
- **`migration_baseline_gate_test.go`** — four cases through the existing fake driver: a populated
  catalogue skips it (no SQL, no ledger), an empty one applies and records it, the other steps are
  unaffected (and a second run applies nothing), and an unreadable catalogue is refused rather than
  read as empty.
- **`fakedriver_test.go`** — the scripted fake models the ledger (`to_regclass('applied_migrations')`,
  the ledger SELECT, the `CREATE TABLE`, the `INSERT`), so the gate and ledger paths are exercisable
  through the existing `Sessions`/`DBTX` seam without adding an interface for a test.
- **`migrations/README.md`** — the bullet that said no `0001` file exists yet now states the baseline's
  contract: generated, frozen, applied only to an empty catalogue, guarded by the parity test.

## Measured, this seat, on scratch databases (PostgreSQL 16.4, `127.0.0.1:55451`)

| what ran | result |
|---|---|
| `0001_baseline.sql` alone, executed on an EMPTY scratch database | applies clean: **47 tables / 505 columns / 132 constraints / 152 indexes** |
| the real boot path (`CreateTables` → `createAll` + ensurers + `Runner.Apply`), full registry, run TWICE on a fresh scratch database | **41 tables / 456 columns / 118 constraints / 126 indexes**; the baseline was SKIPPED (log line, and `applied_migrations` does not exist afterwards); a seat table from an appended registry present, so the registry was complete |
| the two compared catalog by catalog | the tables only the file has are exactly the **6 `ProductionTables`**; on the 41 shared tables: **0 differing columns, 0 differing constraints, 0 differing indexes** (names AND definitions, `information_schema` + `pg_constraint` + `pg_indexes`) |
| the redundant coverage question: the embedded init SQL against the file | its **22** tables are all in the baseline; **0** init tables have a column the baseline lacks; it carries **0** `ALTER TABLE ... ADD COLUMN` |
| the parity guard, RED FIRST | with one table renamed in the file (`seats` → `seats_renamed`), the guard FAILS naming both directions — "registered at runtime but absent from 0001_baseline.sql" and "present in 0001_baseline.sql but no TableDef registers it"; the file was restored byte-identical (sha256 before and after equal) and the guard passes again |
| the OTHER direction, the one the row's acceptance names — a perturbed GO definition | `go test -overlay` over a copy of `models.go` with one column added INSIDE the `tasks` TableDef's DDL literal, so no repo file carried the experiment: FAIL with `table tasks: columns differ between the baseline and the runtime DDL`, both lists printed (`zz_perturbed` in the runtime set only); the same bytes at the delivered tree PASS and `models.go` is clean. A schema test never seen to fail was the object this rig hunts, so it is shown red in both directions |

## A pre-existing defect this found, NOT fixed here

The init SQL path cannot complete on an EMPTY database: `init_schema_postgresql.sql:521` creates the
INDEX `uq_cache_context` and `:608` adds a CONSTRAINT of the same name on the same table — PostgreSQL
refuses the second with `SQLSTATE 42P07 relation "uq_cache_context" already exists` (confirmed directly
on a scratch database). `ExecuteInitSQLFile` runs every statement in ONE transaction and rolls back on
the first failure, so a fresh database gets none of the init SQL — meaning a fresh boot today ends up
with `createAll`'s 41 tables and none of the 6 `ProductionTables`, `applied_migrations` being created
on demand by the runner. That is why the boot path's arm of the comparison above is 41 tables and not
47. It is untouched by this commit and reported to the lead: the fold's file carries all 47 and applies
cleanly, but "the old way" cannot be measured end to end until that clash is resolved.

## What is deliberately NOT in this change

The cutover (deleting `createAll`, the init SQL and the ensurers so the migrations become the only
schema creator — ruled OUT of this commit), the ensurers' split to the cutover (ruled ON the cutover),
and the owner's baseline mark for a database that already has the schema. `MarkBaseline` exists so that
mark CAN be made; making it touches production and is not this seat's decision.

## Battery

From `agenthub_go` with `GOCACHE` and `TMPDIR` in-tree: `gofmt -l` over the tracked `.go` files printed
nothing; `go build ./...` rc 0; `go vet ./...` clean; `go test -count=1 ./...` → **141 packages ok, 0
FAIL**. With `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres` the DB-gated
cases ran and passed: `TestRealPostgresCreateTablesAndSessions`, `TestApplyRecordsEachStepAndASecondRunAppliesNothing`
(which asserts the ledger does NOT exist after the boot path built its database — the skip, on a real
database), `TestAFailedStepRecordsNothingAndLeavesNoneOfItsOwnEffect`, `TestMarkBaselineRecordsAStepWithoutRunningIt`
and `TestEveryTableDefColumnHasAPath`. `TestProductionModelsCRUDRealPostgres` skips on its own
pre-existing gate (`TEST_DATABASE_URL` unset). The throwaway generator and the two scratch-database
drivers were deleted; the only new file is the baseline itself.
