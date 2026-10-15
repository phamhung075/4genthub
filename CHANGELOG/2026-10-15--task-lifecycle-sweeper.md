## 2026-10-15 - Task lifecycle sweeper

### Added
- `agenthub_go/fastmcp/task_management/application/services/task_lifecycle_sweeper.go`: the owner's ruling as one periodic sweep. Three rules over the task table, each age from the environment (`TASK_SWEEP_INTERVAL` 1h, `TASK_PRUNE_AFTER` 7d, `TASK_ESCALATE_AFTER` 24h, `TASK_BLOCK_AFTER` 7d): a completed task past the prune age is deleted, an open task past the escalate age climbs ONE priority level with a note that names the step, an open critical task past the block age becomes `blocked` with `no progress for N days at critical priority`, and `blocked` is never pruned or escalated. An absent variable takes its documented default, a malformed one is an error.
- `agenthub_go/fastmcp/task_management/domain/entities/task_audit_record.go` + `infrastructure/database/task_audit_tables.go` + `infrastructure/repositories/task_audit_record_repository.go`: the audit trail (`task_audit_records`), append-only. One record per escalation, block and prune carries the task id, title, status, priority, completion summary, evidence and the task's own `created_at`/`updated_at`/`completed_at`.
- `migrations/0001_baseline.sql`: the trail's table, matching the Go definition (the parity guard reads both).
- `agenthub_go/fastmcp/server/httpapp/task_sweeper_wiring.go`: the composition - the candidate read over `tasks`, the writes through one task facade per owner, the audit repository, and `NewTaskLifecycleSweeper`.
- `agenthub_go/cmd/agenthub/main.go`: the sweep is started under `sigCtx` as one goroutine, before the server binds.

### Changed
- `task_audit_records.task_id` carries **no foreign key**, unlike every other task-owned table: the record a prune writes must survive the row the delete cascade removes, which is what "evidence is kept" reduces to.
- Every escalation, block and delete goes through the task facade's own use cases, so the `TaskUpdated` events, the `status_changed`/`progress` ledger entries, the cascading delete and the websocket frames are exactly the ones a normal change produces. The priority and status moves stay the entity's `UpdatePriority`/`UpdateStatus`, so the domain's transition rules still decide what is reachable.
- The sweep passes through ONE Postgres advisory lock (`pg_try_advisory_xact_lock(hashtext('task_lifecycle_sweeper'))`, on a session of its own): a second instance SKIPS the interval instead of queueing a second sweep behind the first. The lock lives in that session's transaction, so it is released when the sweep returns, panic included.
- The sweep's own writes run in transactions of their own (the lock session's transaction is not on their context), so each task's change commits and broadcasts like any other change.

### Known, deliberate deviations from the guide's table
| Row | What the code does | Why |
|---|---|---|
| block an open critical task | `in_progress` is blocked; `todo`, `review` and `testing` are logged as refused and stay critical | `value_objects.taskStatusTransitions` does not let those three reach `blocked`, and the guide requires the transition rules to be kept - the sweep does not invent a path the domain forbids |
| record order | the audit record is written BEFORE the change it describes | a change that lands is then never unrecorded; a write that fails leaves a record of the attempt, and the next interval retries the change |
| first sweep | runs at boot, then once per interval | a restart loop would otherwise postpone enforcement indefinitely |

### Testing
- Unit (no database): `TestTaskLifecycleSweepTableOverAFakeClock` - table-driven over a fake clock, every row of the guide's table plus `done 6d old is kept`, `blocked is untouched`, `critical stays critical until the block age`, `a pruned task has exactly one audit record carrying its summary`; `TestTaskLifecycleSweepClimbsOneLevelPerInterval`; `TestTaskLifecycleSweepKeepsThePrunedTasksEvidence`; `TestTaskLifecycleSweepDoesNotRunWhileAnotherInstanceHoldsTheLock`; the `TASK_*` env contract (defaults, every variable read, eight malformed spellings rejected).
- PostgreSQL (`AGENTHUB_TEST_PG_URL`): `TestTaskLifecycleSweepOnPostgres` (the prune's cascade takes the task's ledger rows while the record survives with summary, evidence and timestamps; the escalation's priority moves one level with its note in the task's own ledger; the blocked and the young rows are untouched), `TestSweepAdvisoryLockIsExclusiveOnPostgres` (a held sweep refuses a second attempt and releases on return).
- `agenthub_go/fastmcp/task_management/infrastructure/database/task_audit_tables_test.go`: the table is registered, declares no foreign key, and its kind CHECK matches the Go vocabulary - no database needed.
