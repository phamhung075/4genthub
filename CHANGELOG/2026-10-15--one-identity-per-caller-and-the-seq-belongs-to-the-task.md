## One identity per caller, and the task's seq belongs to the task

### Fixed

- `agenthub_go/fastmcp/server/httpapp/context_ledger_appender.go` (new), wired in
  `agenthub_go/fastmcp/server/httpapp/app.go`: the task-level context event is now appended under the
  **caller's resolved id**, resolved per append from the request context with the same normalization the
  task ledger's other writers use (`auth_helper` -> `domain.ValidateUserID`). It was
  `NewTaskEventRepository(sessions, "", "")` - one value, built once in `NewApp`, whose `user_id` was the
  empty string for EVERY caller. A request whose caller cannot be resolved appends nothing and says so
  instead of writing a row under an empty id.
- `agenthub_go/fastmcp/task_management/infrastructure/repositories/task_event_repository.go`: `seq` is
  computed over the **task**, which is the domain `uq_task_event_seq` states it over - the read was
  `"user_id" = $1 AND "task_id" = $2`, one user's rows for the task. A second lock is taken for the task
  (`lockTaskAppend`, the two-argument advisory-lock form under a fixed first key), after the per-user lock
  and never before it: one user lock then one task lock per append, in that order, so no two appends can
  wait on each other. `AppendInTx`'s doc comment carried "one lock, keyed on the user, both sequences: do
  not improve this into two"; that sentence is replaced by the order rule and the measurement that forced
  the second lock.
- `agenthub_go/fastmcp/task_management/application/services/unified_context_service.go`: a failed context
  event append is LOGGED. It was `_, _ = s.EventAppender.Append(...)`, so the loser of the collision
  vanished without a word - which is why the defect looked task-specific and silent.

### Impact

- `manage_task(action=update)` answered
  `Unexpected error: ERROR: duplicate key value violates unique constraint "uq_task_event_seq" (SQLSTATE 23505)`
  **deterministically on a freshly created task**, with and without a status change, while `get` showed the
  row unchanged (the whole update transaction, this append included, rolled back). One task therefore could
  not carry its own state at all: task `81c907dc` (the C3 close-out) had to be tracked on the rail instead.
- Reproduced by `go-dev` 2026-10-15 on the deployed store: task `4aade366` created 05:30:39Z, first update
  05:33:53Z -> 23505. A second probe, `b4af28d1` created 05:35:57Z, wrote NO row under the caller at all
  (the ledger's user cursor stayed at 1576), which is the same defect seen from the other side: the create's
  context event went in under the empty id.
- Tasks whose ledger ALREADY holds a row under another id (the empty one included) are unblocked by the
  task-scoped `seq`, not by the identity alone: those rows keep their `seq`, and the caller's next append
  takes the number after them. No row is re-attributed - the empty id records no caller, so there is nothing
  to re-attribute it to - and no row is deleted.
- The deploy is the owner's gate: this is a change to the server that answers `api.4genthub.com`, so the
  acceptance (`update` on `81c907dc` succeeds) can only be observed after it ships.

### Testing

- `agenthub_go/fastmcp/task_management/infrastructure/repositories/task_event_repository_test.go`:
  `TestTaskEventAppendTakesTheNextTaskSeqAcrossTwoWriterIdentities` (PostgreSQL-gated). Two identities,
  one task: the first appends the context event's position, the second must take the NEXT seq rather than
  collide, and the caller's own scoped read holds exactly its entry. FALSIFIED, not asserted: with
  `task_event_repository.go` reverted to HEAD the case FAILS with
  `ERROR: duplicate key value violates unique constraint "uq_task_event_seq" (SQLSTATE 23505)` - the
  production error, reproduced against `tools/testpg/start.sh`.
- `agenthub_go/fastmcp/server/httpapp/context_ledger_appender_test.go` (new, no database):
  `TestContextLedgerAppenderRefusesWithoutAResolvedCaller` passes.
- MEASURED: the four `TestTaskEventAppend*` cases PASS against the throwaway cluster
  (`AGENTHUB_TEST_PG_URL=postgresql://... go test -count=1 -run TestTaskEventAppend ./fastmcp/task_management/infrastructure/repositories/`, 7.1 s). With the URL absent the PostgreSQL-gated cases skip, and
  `go test -count=1 -run 'TestContextLedgerAppender|TestTaskEventAppend' ./fastmcp/server/httpapp/
  ./fastmcp/task_management/infrastructure/repositories/` prints `ok` for both. `go build ./...`, `go vet` on
  the three touched packages and `gofmt -l` on the six touched files are clean.
