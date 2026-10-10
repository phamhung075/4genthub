## A fresh-database boot was measured before the current-user bootstrap was deleted

Ruling: delete `InitializeDatabaseForCurrentUser` only if a fresh-database boot on the live path proves its job is done elsewhere. This entry records the proof, the one clause of the guard the measurement corrected, and the half of the bootstrap that was **not** proven and is therefore named rather than implied.

### How it was answered

A throwaway program (under `agenthub_go/.gotmp/liveboot/`, run once and deleted) created a fresh database on the throwaway PostgreSQL and booted the live path alone — `deps := database.OSDeps()`, `database.InitDatabase(ctx, deps)`, `AUTO_MIGRATE=true`: the same calls `cmd/agenthub/main.go` makes, with the `DATABASE_*` variables pointed at the new database. It then read the state back.

### What the boot alone reached

- The four tables `EnsureTablesExist` checks — `projects`, `project_git_branchs`, `tasks`, `subtasks` — all present, and 21 tables in total.
- `tasks.progress_state`, `subtasks.progress_state` and `tasks.subtask_count` all present; `tasks.details` absent, as `O1c` intends.
- So all three END STATES the STEP 0 guard names are reached by the live path alone: the schema gate inside the bootstrap is duplicated, and that is what authorised the deletion.

### The clause the measurement corrected

The guard counted the `uuid-ossp` extension as part of the state, because `init_schema_postgresql.sql:10` creates it. Measured: the fresh database has `plpgsql` and **no** `uuid-ossp`, and `tasks.id` carries no default at all. `createAll` builds its DDL from the Go table registry (`models_prod.go`), not from the embedded schema, so nothing it creates calls `uuid_generate_v4()` and the extension is not needed. It is also not a privilege limit: running `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` against that database in the same session succeeded. The extension line belongs to the init-SQL path, which runs it itself. The claim in the `a2050430` entry that "a fresh database still gets the extension on the live path" is corrected there in place, and this is the measurement that corrected it.

### Changed

- `agenthub_go/fastmcp/database_init.go` — `InitializeDatabaseForCurrentUser` and `InitializeForUser` deleted. Neither ran: their only caller was `RunStartupMigrations`, which had zero callers.
- Kept, and this is the point: `EnsureTablesExist` and `CreateDefaultProject`, with their integration case. The capability the bootstrap would exercise survives; only the never-run wiring went.

### Named rather than implied: the half that was not proven

The bootstrap did two things. The schema gate was proven duplicated. The other half — creating a default project and branch for the current user — is **not done anywhere else**: the live boot left `projects` and `project_git_branchs` at zero rows, no HTTP route or frontend code creates a "My First Project", and because `RunStartupMigrations` never ran, the Go server has never performed that step at all. Deleting the wrappers therefore also removes the only boot-side expression of it, which is why it is called out here rather than left for someone to rediscover.

Wiring it back is a product decision, not a cleanup: the function fell back to a hardcoded `default-user-001` when neither `CURRENT_USER_ID` nor `DEFAULT_USER_ID` was set, so an unconditional call after `InitDatabase` would create a project for a fabricated user on a real deployment. If a boot-time default project is wanted, the call belongs in `cmd/agenthub/main.go` directly after `InitDatabase`, with a real user id and no fallback; `CreateDefaultProject` is kept for exactly that call, and its integration case still passes.
