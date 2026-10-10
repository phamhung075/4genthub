## The legacy details migration leaves before the column it feeds does

### Changed

- `agenthub_go/fastmcp/database_migrations.go` — deleted whole: `DatabaseMigrator`, `NewDatabaseMigrator`, `isPostgresURL`, `RunMigrations`. After `RunStartupMigrations` went (a2050430) the only reachable member was `RunMigrations`, and its only callers after that were two tests.
- `agenthub_go/fastmcp/database_migrations_test.go` — deleted whole: `TestIsPostgresURL` pinned the scheme-acceptance rule that existed only to guard `RunMigrations`.
- `agenthub_go/fastmcp/database_init_integration_test.go` — `TestDatabaseMigratorRunMigrations` removed; the file keeps `TestDatabaseInitializerCreateDefaultProject` and its helper.
- `agenthub_go/fastmcp/database_init_test.go` — `TestDatabaseMigratorURL` removed; the file keeps `TestDatabaseInitializerURL`.

### Why, in one sentence

The legacy `details` → `progress_history` move is a migration **into a column O1c is deleting**, so it is dead twice over: test-only in production, and aimed at a target that is going away.

### The property was kept, not dropped with the test

`TestDatabaseMigratorURL` asserted that an explicitly passed URL wins over the one built from the environment. That property belongs to the live path, and `TestDatabaseInitializerURL` already asserts it there — for the explicit URL *and* for the environment-built one (`postgresql://u:p@h:1/db`), so the claim survives against the code that remains. `TestIsPostgresURL` is the deliberate exception: nothing in the live path branches on the DSN scheme, so that rule had no property to keep. It is a test deleted because its subject was deleted, not an assertion quietly dropped.

### Testing

From `agenthub_go` (`GOCACHE`/`TMPDIR` in-tree, throwaway PostgreSQL on 55432):

- `gofmt -l fastmcp/` printed nothing; `go build ./...` ok; `go vet ./fastmcp/` clean.
- A word-boundary sweep for `RunMigrations|DatabaseMigrator|isPostgresURL|NewDatabaseMigrator` over every tracked `.go` file prints nothing.
- `go test -count=1 ./fastmcp/` ok with the PostgreSQL URL set, so the integration case that remains (`TestDatabaseInitializerCreateDefaultProject`) ran rather than skipped.
