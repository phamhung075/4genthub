# The migration runner and its ledger writer land — T12's mechanism, not the fold

T12 rules that one ordered set of embedded migrations becomes the only DDL source. This lands the
**mechanism**: the runner, the ledger writer, and the boot wiring. The fold of today's DDL sources
into a `0001` baseline is the rest of stage 1 and is deliberately **not** here — no migration file
exists yet, so the embedded set is empty and nothing runs in production.

## What landed

- **`fastmcp/task_management/infrastructure/database/migration_runner.go`** — `Migration`,
  `LoadMigrations` (`go:embed migrations` over `migrations/*.sql`, filename order, which for
  zero-padded names is numeric order), `Runner.Apply` and `Runner.MarkBaseline`.
- **Each step is its own transaction**, holding its SQL and its ledger row: a step whose SQL fails
  records nothing and leaves none of its own effect behind, while the steps before it stay applied and
  recorded, so the next run resumes where this one stopped. One transaction for a whole run would roll
  its earlier successes back and re-run them — which is how a runner loses the record of what ran.
- **The ledger is the EXISTING `applied_migrations` table** (`models_prod.go:118`), adopted rather than
  a new `schema_migrations`. A row exists exactly when a step applied: the table's legacy `success` /
  `error_message` columns are never written, because a failed step rolls back and records nothing at
  all. That is a deliberate departure from the Python runner, which kept failure rows.
- **The ledger read happens under a transaction-scoped advisory lock**
  (`pg_advisory_xact_lock(hashtext('agenthub_schema_migrations'))`), so two processes booting at once
  cannot both decide a step is unapplied: "is it applied?" and "record that it is" are one decision,
  not two a second boot can interleave with.
- **The runner owns its bookkeeping.** On a database that lacks `applied_migrations`,
  `ensureLedgerInTx` creates it from the SAME declaration the schema carries (`ProductionTables`), so
  the ledger is not a second hand-written copy of its own table; a database that already has it is
  left untouched. Nothing else about the schema is created or altered here — the larger question that
  the registry's tables and the production tables are created by two different paths is the "exactly
  one schema creator" row, untouched by this change.
- **Wired where the DDL already runs**: `DatabaseConfig.CreateTables` calls the runner after
  `createAll`, `EnsureAIColumnsExist` and `RunColumnEnsurers`, so a step sees the schema as those leave
  it. With today's empty set the call is a no-op: no transaction, no ledger read.
- **`migrations/README.md`** states the directory's contract: `NNNN_slug.sql`, the file's base name is
  the name `applied_migrations` records, never rename or reorder an applied file, and `0001` is the
  baseline of the database that already exists — whose **mark is the owner's** action (it touches
  production), not the runner's.

## What is deliberately NOT in this change

The fold of the seven `TableDef` sets and the embedded init SQL into a `0001` baseline (the rest of
stage 1), the schema-versus-migrations parity guard, and the owner's baseline mark. `Runner.MarkBaseline`
exists so that mark CAN be made; making it is not this seat's decision.

## Tests, and what each one pins

From `agenthub_go`, with `AGENTHUB_TEST_PG_URL` supplied by `bash tools/testpg/start.sh`:

| test | what it proves |
|---|---|
| `TestLoadMigrationsOrdersByFilenameAndNamesEachStepByItsFile` | filename order, the extension stripped from the recorded name, non-SQL files ignored |
| `TestValidateSetRefusesWhatTheRunnerCannotApplyUnambiguously` | a duplicate name, a name out of order, a step with no name and a step with no SQL are each refused, by name |
| `TestTheEmbeddedSetIsWellFormed` | the set a boot actually applies loads and validates |
| `TestApplyRecordsEachStepAndASecondRunAppliesNothing` | both steps apply in order and are recorded; **the second run applies nothing** and does not repeat the insert; and the ledger table is created on first use, since the throwaway database is built by the registry alone |
| `TestAFailedStepRecordsNothingAndLeavesNoneOfItsOwnEffect` | a step that creates a table and then raises leaves **no ledger row and no table** (its own transaction), while the step before it stays applied and recorded |
| `TestMarkBaselineRecordsAStepWithoutRunningIt` | marking records the name **without executing its SQL**, a later run then applies nothing, and a name the set does not contain is refused rather than marking nothing |

Battery, from `agenthub_go` with `GOCACHE` and `TMPDIR` in-tree and the database present:
`gofmt -l cmd fastmcp internal` printed nothing; `go build ./...` BUILD_OK; `go vet ./...` VET_OK;
`go test ./...` zero failures (`grep -cE '^(FAIL|--- FAIL)'` = 0).
