# Task lifecycle sweeper (server)

Owner ruling, 2026-10-15: a task must end `done` or `blocked` after it is created. The server enforces this with one periodic sweep; nothing depends on a seat remembering.

## Rules

| Task state | Age rule | Action |
|---|---|---|
| `done` / `cancelled` / `archived` | `completed_at` (or `updated_at`) older than `TASK_PRUNE_AFTER` (default 7d) | delete through the application layer (domain events cascade subtasks, assignees, context; the schema has no `ON DELETE CASCADE`) |
| `todo`, `in_progress`, `review`, `testing` | `updated_at` older than `TASK_ESCALATE_AFTER` (default 24h) | raise priority one level (`low`→`medium`→`high`→`urgent`→`critical`) and write a progress note naming the step; a task that was escalated has `updated_at` bumped, so it climbs one level per interval, not all at once |
| the same states | already `critical` and still older than `TASK_BLOCK_AFTER` (default 7d) | set `blocked` with blocker text "no progress for N days at critical priority", so a human sees a decision is owed |
| `blocked` | none | never pruned or escalated; the blocker text is the record |

## Constraints

- Intervals come from environment variables; no number is hard-coded except the documented defaults. Missing variables use the defaults, malformed ones fail startup.
- One sweep per interval (`TASK_SWEEP_INTERVAL`, default 1h), started in `cmd/agenthub/main.go` under `sigCtx`, guarded by a Postgres advisory lock so two server instances do not sweep twice.
- Every escalation, block and delete is written to the audit trail and publishes the normal task events, so the UI updates over the websocket like any other change.
- Priority and status changes go through `Task.UpdatePriority` / `Task.UpdateStatus`, which keep the transition rules; no direct SQL updates.
- Tests: table-driven sweep over a fake clock (each row of the table, plus "done 6d old is kept", "blocked is untouched", "critical stays critical until the block age").

## Open point for the owner

"Complete" tasks are deleted, so their completion summary and evidence disappear. If the audit trail must keep them, the sweep archives instead of deleting (`status=archived`) and a second, longer rule deletes archived tasks. Default until ruled: delete.
