# The schema's migrations

One file per step, named `NNNN_slug.sql`. `NNNN` is the order; the file's base name without `.sql` is
the name `applied_migrations` records. `migration_runner.go` reads this directory with `go:embed`,
sorts by filename, and applies every step the table does not already record - each step in its own
transaction, together with its ledger row.

- **The name is the step's identity.** Never rename or reorder a file that has been applied anywhere:
  the recorded name is how the runner knows the step ran.
- **Non-SQL files here are ignored** by the loader. This file exists to state the naming rule the
  loader enforces.
- **`0001` is the baseline of the database that already exists.** `0001_baseline.sql` is GENERATED
  from the runtime TableDef registry (the aggregate `taskdb.Tables`, then `ProductionTables`) and is
  FROZEN: never rename or reorder it once it has been applied anywhere. Only a database with an EMPTY
  catalogue receives it, because `migration_runner.Apply` skips it when the catalogue already holds
  tables - the same rule `db_initializer.go` applies to the init SQL. The runner NEVER auto-adopts: on
  a database that already has the schema the mark is recorded only by `Runner.MarkBaseline`, an owner
  action. Because `createAll` populates the catalogue before the runner runs, a FRESH boot is in that
  state too, so any step that depends on the mark - currently
  `0003_progress_history_carry_and_drop` - refuses (`SQLSTATE P0001`, naming the mark to run) until the
  owner has marked, including on a database that has never held the columns that step drops.
  `schema_matches_definitions_test.go` holds the registry to the embedded
  set of steps, and to THIS file, which must never drop or alter a column.
