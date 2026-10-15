## The progress-notes backfill, before the switch

### Added
- `agenthub_go/fastmcp/task_management/infrastructure/database/migrations/0002_progress_notes_backfill.sql`: the additive half of O1c that the frontend gate stopped on. Every progress note stored ONLY in `tasks.progress_history` or `subtasks.progress_history` is copied into `task_events` as a `progress`/`human` entry, so the ledger alone is complete and the dialog's ledger timeline stops missing pre-switch notes.
  - The carried payload is the append path's own shape - `content` (with its numbered header, as the column stores it), `progress_number`, `timestamp` - plus `carried_from`, the column key it was copied from. `ProgressTextWith` merges the two sources by content and number, so a carried copy of a note that is already in the ledger renders once, not twice.
  - It is `human` and `user_id`-attributed because that is what the note was: the user's own write, made before any seat attributed them. The actor vocabulary is closed (`seat`, `client`, `gate`, `human`) and was not widened to describe a migration.
  - Before numbering, it takes each affected user's advisory lock in the SAME key the append path takes, because the runner's own lock is a different key: without it the `MAX+1` numbering could race a live append and either side could collide on the uniques.
  - `to_jsonb()` rather than `json_each`/`jsonb_each` directly: the live column is `json` (the table definitions) while the DDL source says `jsonb`, and each `_each` accepts only its own type.

### Changed
- Five cases in `agenthub_go/fastmcp/task_management/infrastructure/database/` moved because the embedded migration set is non-empty for the first time - see `TEST-CHANGELOG.md`, 2026-10-11. `NEXT_GEN.md`'s O1c box carries the record of what landed, what did not, and the two deliberate differences from the ruled step.

### Verified
- `gofmt -l` empty on all four touched Go files; `go build ./...` rc 0; `go vet ./...` rc 0.
- `go test ./fastmcp/task_management/infrastructure/database/...` green with `AGENTHUB_TEST_PG_URL` (all cases, including the two new ones and the five moved ones).
- Measured on a real PostgreSQL: with `entities.Task{}.ProgressTextWith(events)` - the call the task dialog makes, over the LEDGER's events alone - a column-only note is invisible before the step and visible after, exactly once, for both a task's note and a subtask's; the carried rows read `progress`/`human` with `carried_from` and a `user_seq` of at least 1, and the subtask's copy names its subtask while the task's own copy has `subtask_id` NULL; a second application adds nothing; a note the ledger already holds is not copied at all.

### Not done, and named
- The ruled carry step is NOT this one. `NEXT_GEN.md` O1c (decision D1 3a) rules a step that ALSO drops `progress_history` and `progress_count`, and it runs only under the owner's `0001` baseline mark; its own check ("3 entries -> 3 equal events, both columns gone") is not met here, and a malformed entry is skipped rather than failing the step, because a step that destroys nothing has nothing to protect.
- `config.ReleaseVersion` is untouched: production already reports 0.0.36, so there is no release for this change to name.
