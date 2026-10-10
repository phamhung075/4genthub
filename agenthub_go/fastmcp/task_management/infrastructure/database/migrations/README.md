# The schema's migrations

One file per step, named `NNNN_slug.sql`. `NNNN` is the order; the file's base name without `.sql` is
the name `applied_migrations` records. `migration_runner.go` reads this directory with `go:embed`,
sorts by filename, and applies every step the table does not already record - each step in its own
transaction, together with its ledger row.

- **The name is the step's identity.** Never rename or reorder a file that has been applied anywhere:
  the recorded name is how the runner knows the step ran.
- **Non-SQL files here are ignored** by the loader. This file exists to state the naming rule the
  loader enforces.
- **`0001` is the baseline of the database that already exists.** The runner does not mark it on its
  own: on an existing database the mark is an owner action (`Runner.MarkBaseline`), because it touches
  production, and on a fresh database the baseline would execute. No `0001` file exists yet - folding
  today's DDL sources into it is stage 1 of T12, not the slice that landed the runner.
