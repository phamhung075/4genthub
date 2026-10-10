### Added

**Startup names the tables the database lacks** (2026-10-03)

- A server started without `AUTO_MIGRATE=true` on an empty database answered healthy and then 500 `relation "machines" does not exist`. `InitDatabase` now logs, once at startup, `database: N table(s) missing: a, b, ...; queries on them fail with 500 until the schema exists. Start once with AUTO_MIGRATE=true to create it` (`task_management/infrastructure/database/missing_tables.go`, `MissingTables` over the one `Tables` registry, which includes the seat tables). It creates nothing and does not stop the server. Checked on a real empty Postgres: 38 tables named, server still listens.
