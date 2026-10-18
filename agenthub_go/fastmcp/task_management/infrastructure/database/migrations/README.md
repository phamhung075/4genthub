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
  action. A FRESH boot is NOT in that state: the steps are the only schema creator (the seat-tier
  decision of 2026-10-17 deleted `createAll` and the column ensurers), so an empty database receives
  `0001` and records it in the same transaction. The state that refuses is a catalogue some OTHER
  creator built - every database a pre-2026-10-18 boot left behind - where `0001` is skipped without a
  row and any step that depends on the mark, currently `0003_progress_history_carry_and_drop`, refuses
  (`SQLSTATE P0001`, naming the mark to run), including on a database that has never held the columns
  that step drops.
- **Columns a database may predate are a step of their own.** `0005_patch_columns_the_boot_added.sql`
  carries the columns the deleted ensurers patched in (and their indexes and CHECKs), every statement
  idempotent, so a fresh database that took them from `0001` is a no-op; `0006_task_event_vocabularies.sql`
  re-creates the two `task_events` CHECKs separately, because validating every row must not take the
  columns down with it when a row carries a kind the narrowed vocabulary no longer has.
  Two guards hold the baseline. `schema_matches_definitions_test.go` holds the registry to the embedded
  set of steps, so every registered table, column and index is created by one of them, and
  `one_schema_creator_integration_test.go` holds the OTHER direction - a table only `0001` defines is
  not recreated on a catalogue where `0001` is skipped, which is what a second creator would do.
  `migration_baseline_parity_test.go` holds `0001_baseline.sql` back to the registry it was generated
  from, comparing column names, referenced tables and CHECK expressions. The baseline itself must never
  drop or alter a column.
