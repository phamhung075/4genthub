# The boot has one schema creator

Date: 2026-10-18. Hub task `bb83e9b2-efa8-4180-9367-2a17c72cce14`, queue row
`qitem-20261017221351-c241c407bf3e`. The owner call the row was blocked on
(`qitem-20261017224516-1b83ee55df16`) chose option A: the embedded migrations.

## What the tree held at HEAD

One boot ran FOUR schema creators in sequence (`db_initializer.go`, `database_config.go`):

1. `createAll` — the Go `TableDef` registry, creating missing tables and enum types.
2. `EnsureAIColumnsExist` — `ALTER TABLE … ADD COLUMN` for the seven `ai_*` columns on `tasks` and
   `subtasks`, gated on `AUTO_MIGRATE`.
3. `RunColumnEnsurers` — five registered ensurers: `session_columns.go` (agent_sessions),
   `task_event_ensurer.go` (task_events columns, uniqueness and the two closed vocabularies),
   `completion_attribution_ensurer.go`, `acceptance_scope_ensurer.go`, `ensure_seat_columns.go`.
4. The migrations, last, against whatever 1–3 had left.

So the same column could be written by two paths, and the second boot of a database whose shape
differed from the registry's could leave the two disagreeing with nothing to report it.

## What changed

- **`CreateTables` is the migration set, and nothing else.** `createAll`, the critical-table re-check
  and `RunColumnEnsurers` are deleted; `EnsureAIColumnsExist` becomes a READBACK (`ensure_ai_columns.go`,
  48 lines) that reports the columns the steps create and no longer writes them.
- **The ensurers' statements are steps.** `0005_patch_columns_the_boot_added.sql` carries the column
  work verbatim (`acceptance_criteria`, `scope`, `completed_by`, the `ai_*` set, `agent_sessions`'
  identity/cursor/state and its both-or-neither CHECK, `rooms.team_id`, `room_decisions.acked_at`,
  `task_events.user_seq` with the per-user backfill, `client_event_id` and both uniques) — every
  statement `IF NOT EXISTS` or guarded, so a fresh database, which takes them from `0001`, is a no-op.
- **`0006_task_event_vocabularies.sql`** holds the two re-created CHECKs, a separate step because the
  former ensurer deliberately committed them separately: a legacy database whose rows carry a deleted
  kind is REPORTED with its count (the six removed kinds are named) instead of failing on a constraint.
- **`one_schema_creator_integration_test.go`** pins it by BEHAVIOUR, not by reading source: on a
  catalogue that already holds tables (the state where `0001` is skipped), `labels` - a registry table
  only `0001` creates - is dropped and the boot must NOT put it back. `createAll` does; the steps do
  not. Red before: on a `worktree` of HEAD `8f053e8c` the same case fails with "the boot recreated a
  table only 0001_baseline defines".
- **`ResetDatabase`** drops `applied_migrations` with the tables and calls `CreateTables`, so the next
  Apply runs every step from an empty catalogue instead of skipping a ledger whose rows outlived the
  schema.
- Deleted with their tests: `column_ensurers.go`, `session_columns.go`, `task_event_ensurer.go`,
  `completion_attribution_ensurer.go`, `acceptance_scope_ensurer.go`, `ensure_seat_columns.go`, and the
  `create_tables_guard_test.go` / `column_paths_test.go` gates that held the registry to `createAll`.

## Measured

- **A fresh boot, from the built binary.** A new empty database, `AUTO_MIGRATE=true`, port 18000:
  `/health` answers `healthy` and `manage_task list` answers
  `{"success":true,…"total":0}`, so the steps created the board the read path queries.
- **`TestALegacyDatabaseGainsThePatchedColumnsFromTheSteps`** (new, PG): a catalogue holding only the
  pre-`0005` columns and a row with events gains `acceptance_criteria`, `scope`, `completed_by`, the
  `ai_*` set and `task_events.user_seq` backfilled to 1,2,3; a second boot applies nothing.
- **`TestTheBootRefusesTheCarryStepOnAPopulatedDatabaseWithoutTheMark`** now builds a legacy stale
  catalogue (schema present, `applied_migrations` cleared, the four pre-drop columns restored) and
  proves the boot still REFUSES at `0003` for the missing `0001_baseline` mark and leaves the columns
  in place. Its old premise ("`createAll` has just built it") named deleted code.
- **`TestSchemaMatchesGoDefinitions`** compared index lists, so the same `CREATE INDEX IF NOT EXISTS`
  in `0001` and `0005` read as a mismatch. It now compares each table's indexes as a set: an index is
  its name and definition, not the number of steps that mention it.

## Checks

- `go build ./...`, `gofmt -l`, `go vet ./...`: clean.
- `go test ./fastmcp/task_management/... ./fastmcp/seat_management/... ./fastmcp/session_stream/... -count=1`
  against the local cluster: all packages ok.
- `go test ./fastmcp/server/httpapp/ -count=1`: one failure,
  `TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder` (`handover_malformed`). **Pre-existing**:
  the same case, run in a `git worktree` of the unmodified HEAD (`8f053e8c`), fails identically.
