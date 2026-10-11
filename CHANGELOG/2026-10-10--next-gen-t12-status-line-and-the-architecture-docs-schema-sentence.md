## NEXT_GEN's T12 carries the lead's status line, and the architecture doc's "Schema today" takes the tree as it is

### Fixed
- `agenthub_go/NEXT_GEN.md` T12 (`:646`): a new sub-line at `:649` carries the lead's status line **verbatim**, with its attribution (the architect's `FINDING-G1-addendum-after-runner-deletion-2026-10-10.md`) and the measurement behind every claim in it.
- `agenthub_go/NEXT_GEN.md` O1c (`:421`): the stale `fastmcp/database_migrations.go` citation is REMOVED, with the reason it cannot be re-pointed — the only evolution path today ADDS columns (`column_ensurers.go:27`, `AUTO_MIGRATE`-gated, idempotent, recording nothing) — and the lead's ruling that T12 is built before O1c.
- `agenthub_go/NEXT_GEN.md` O1a (`:419`): the must-not-touch list's `database_migrations.go` now reads "deleted 2026-10-10, `57b9bb3b`".
- `ai_docs/core-architecture/agenthub-system-architecture.md:347`: the "Schema today" sentence said **four** patchers (`column_ensurers.go`, `ensure_ai_columns.go`, `missing_tables.go`, `auto_migration.go`) and "a PostgreSQL init SQL file inside the Python tree". The live set is THREE — `auto_migration.go` went in `a2050430` and the startup runner `fastmcp/database_migrations.go` in `57b9bb3b` — `CreateTables` calls `EnsureAIColumnsExist` then `RunColumnEnsurers` and nothing else (`database_config.go:458`-`:459`), the init SQL lives at `agenthub_go/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`, `agenthub_go/migrations/` does not exist, the DDL comes from the Go table registry, and the `applied_migrations` ledger is declared with no reader and no writer (`models_prod.go:29`, `:118`-`:125`).

### Verified
- All five facts re-measured at `652895fc` rather than relayed: `git ls-tree -r --name-only HEAD | grep database_migrations` prints nothing; `column_ensurers.go:27` is `func RunColumnEnsurers`; `CreateTables`'s two calls are the ones cited; `ls agenthub_go/migrations/` → No such file or directory; and the patcher files' presence was checked one by one.
- `NEXT_GEN.md:394` (the seat-data-model G1) was deliberately NOT touched: the architect's addendum rules it a different gate, and it is met.
- Source: the lead's row `qitem-20261010173848-4d7e9ccc57c78f81`, answered with this change.
