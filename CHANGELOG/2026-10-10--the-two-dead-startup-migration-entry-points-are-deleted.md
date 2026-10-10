## The two dead startup migration entry points are deleted, and the schema that already carries their work is what made it safe

### Changed

- `agenthub_go/fastmcp/database_migrations.go` — `RunStartupMigrations` deleted. It had **zero** callers in the module, tests included (its only hits were its own definition and its doc comment), so the startup work it sequenced never ran. The live path is `InitDatabase` (`task_management/infrastructure/database/init_database.go`) → `DatabaseConfig.CreateTables`, which applies the embedded schema under `AUTO_MIGRATE=true`.
- Same file — the helpers only that function used: `GetMigrator`, `EnsureDatabaseReady`, the `migratorInstance`/`migratorMu` singleton, and `DatabaseMigrator.InitializeDatabase`. `InitializeDatabase`'s one action, `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`, is already line 10 of the embedded schema, so a fresh database still gets the extension on the live path. The `sync` import went with the singleton, and the file's header comment no longer claims a startup role the file does not have.
- `agenthub_go/fastmcp/task_management/infrastructure/database/auto_migration.go` — deleted whole: `RunAutoMigrations`, the `AutoMigration` type, `RunAllMigrations`, `renameSubtasksTable`, `addProgressStateColumns`, `addSubtaskCountColumn`, `isDuplicateColumnErr`. The module-level function's only non-test caller sat *inside* `RunStartupMigrations`, so the file was dead by transitivity; every member of it was reachable only through that single entry point.

### Why the guard passed, and what it turned on

`RunStartupMigrations` sequenced three steps and `RunAutoMigrations` performed them, so the question was whether deleting them would lose a migration a database still needs. The embedded schema already carries all three **end states**: `init_schema_postgresql.sql:249` creates `subtasks` outright (the rename's destination; the string `task_subtasks` occurs in no `.sql` in the tree), `:259` and `:355` declare `progress_state` on `subtasks` and `tasks` (the column `addProgressStateColumns` added and back-filled — a fresh table has no rows to back-fill), and `:365` declares `tasks.subtask_count`. The extension step is `:10`. A database initialised by the live path therefore reaches the state the deleted functions aimed at.

The rename is the one step the schema carries as an outcome rather than as a statement, because a fresh schema has nothing to rename. Renaming `task_subtasks` preserves the rows of a deployment that still has that table; that is a data operation on a pre-existing database, which is the deferred applied-migrations question rather than this one. It is named here rather than implied.

### Testing

From `agenthub_go` (`GOCACHE`/`TMPDIR` in-tree, throwaway PostgreSQL on 55432 where a database is needed):

- `gofmt -l` on both touched source files printed nothing; `go build ./...` ok; `go vet ./fastmcp/ ./fastmcp/task_management/infrastructure/database/` clean.
- A word-boundary sweep for `RunStartupMigrations|RunAutoMigrations|AutoMigration|EnsureDatabaseReady|GetMigrator` over every tracked `.go` file prints nothing.
- `go test -count=1 ./fastmcp/ ./fastmcp/task_management/infrastructure/database/` — both packages ok (2.4s and 16.5s), with the PostgreSQL URL set so the schema cases ran rather than skipped.
- The gate file's three surviving cases pass by name: `TestInitDatabaseNoDDLWithoutAutoMigrate`, `TestEnsureAIColumnsRespectsAutoMigrateGate`, `TestDBInitializerSkipsInitSQLWithoutAutoMigrate`. `TestRunAutoMigrationsRespectsAutoMigrateGate` existed only to exercise the deleted entry point and is gone with it.
- `auto_migration_test.go` held exactly one case, `TestAutoMigrationRealPostgres`, and was deleted with the file it tested.

### Left standing on purpose, named rather than quietly cut

- `DatabaseMigrator.RunMigrations` is still reached by `TestDatabaseMigratorRunMigrations` (`fastmcp/database_init_integration_test.go`), which observes the real migration: a legacy `details` column is folded into `progress_history` and then dropped. It has no production caller for the same reason the entry points had none, but it **moves data**, which is the applied-migrations class this item put out of scope.
- `InitializeDatabaseForCurrentUser` (`fastmcp/database_init.go`) was called only from `RunStartupMigrations` and is therefore now unreachable, and `InitializeForUser` with it. It is a startup bootstrap rather than a migration, so deleting it is a decision about the live boot rather than about this item.

Both are one ruling away from a second small commit. Nothing is pushed and `/health` was not touched.
