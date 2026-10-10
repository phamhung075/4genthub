### Added

**Startup notice for columns that differ from the ORM definitions** (2026-10-03)

- `task_management/infrastructure/database/missing_tables.go`: without `AUTO_MIGRATE` the server already logged missing tables; it now also compares every registered table that exists with `information_schema.columns` (`ColumnDrift`, one query) and logs, per table, the registered columns the database lacks (queries naming them fail) and the columns the ORM does not know that are `NOT NULL` without a default (inserts fail, e.g. a leftover `seats.status`). Nullable or defaulted unknown columns are not reported. The expected columns come from the `Tables` registry (the ORM definitions), not a second list. Log only: nothing is altered, startup is never stopped; `AUTO_MIGRATE` still creates only missing tables.
- `MissingTables` and `ColumnDrift` return an error for a nil engine instead of dereferencing it; the failure of either check is logged and does not stop startup.
- Verified: gofmt, go vet, `go test ./fastmcp/task_management/infrastructure/database`; mutation checks (ignore blocking columns, ignore missing columns) fail the new tests. Not run against a real Postgres.
