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
  tables - the same rule `db_initializer.go` applies to the init SQL - and on a database that already
  has the schema the runner records it without executing it (`Runner.MarkBaseline`, an owner action,
  because it touches production). `migration_baseline_parity_test.go` holds the registry to the file.
