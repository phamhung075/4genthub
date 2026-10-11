## The ledger checks the subtask an intent names, and one body that was not a list

The ledger MAJOR of the reviewer's gate `1a370e02..4f86a1ac`
(`GATE-4f86a1ac-ledger-p2p3-2026-10-11.md`, row `qitem-20261011002505-066a0c0054f3cf56`), plus the
minor the reviewer could only mark `[INFERENCE]` because a review seat may not author the program
that settles it.

### Fixed

- `subtask_id` was accepted, canonicalised and WRITTEN with no ownership check and no foreign key.
  `task_event_tables.go` gives `task_id` its `REFERENCES tasks(id)` and leaves `subtask_id` with an
  empty `ForeignKey`, so an intent could name a subtask of a DIFFERENT task, or of another user, and
  the row landed in the caller's ledger: every constraint the table has was satisfied. The check is now
  the one the row's own `TaskVisible` comment argues for, one level down from it:
  `SubtaskInTask(ctx, taskID, subtaskID)` —
  `SELECT EXISTS(SELECT 1 FROM subtasks WHERE "user_id" = $1 AND "task_id" = $2::uuid AND "id" = $3::uuid)`
  — user-scoped like every other statement the ledger adds. This is route (a) of the two the reviewer
  allowed: the refusal lives in the application service, beside the task check and BEFORE the decision
  reads, so a refused item still costs no sequence and is still not remembered.
- The token is `unknown_subtask`, and it covers THREE shapes with one string — a subtask that does not
  exist, another user's subtask, and a subtask of a different task — for the reason `unknown_task`
  covers a malformed id and another user's task with one: a token that told them apart would answer
  whether a subtask exists to a user who cannot see it. `invalid_subtask_id` still covers the
  not-a-UUID shape.
- A literal JSON `null` body to `POST /api/v2/ledger/intents` was answered `200 []` while the code's
  own comment claimed the 422 it answers for `{}`: `json.Decoder` leaves a nil slice for `null` and for
  `[]` alike, so the two were indistinguishable where the check was made. The body is decoded into a
  POINTER now, nil only for `null`, and `null` is refused like every other body that is not a list. An
  empty list is still a list, and nothing else about what the route accepts changed.

### Not changed, and deliberately

- `base_seq` AHEAD of the task's current seq stays accepted: no protection is lost — the rule exists to
  refuse a base that is BEHIND, and a future base cannot be stale — and it is a contract observation
  for the client half rather than a defect here.
- `limit` stays uncapped on both reads, exactly as `ListAfter` is: one read's cap would make a page
  mean two different things.

### Files

- `fastmcp/ledger/domain/entities/intent.go` — `ReasonUnknownSubtask`, documented with the three
  shapes it covers.
- `fastmcp/ledger/application/services/ledger_service.go` — `SubtaskInTask` on the `Ledger` port, and
  the check in `submitOne` beside `TaskVisible`.
- `fastmcp/task_management/infrastructure/repositories/task_event_repository.go` — `SubtaskInTask`,
  one user-scoped statement, and the comment saying why the foreign key cannot replace it.
- `fastmcp/server/httpapp/ledger_mount.go` — `ledgerIntentsBody` decodes into a pointer, so a literal
  `null` is not a list; its comment now says what the code does rather than what it was meant to do.
- `fastmcp/server/httpapp/ledger_pg_test.go` — the two cases below and the three fixtures they need.

### Verified

Run in this seat's worktree `wt/go-dev`, branch `4genthub-min/go-dev`, with
`AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55441/postgres` — the port read from that
cluster's `postmaster.pid`.

- SEEN RED FIRST and then green, in the same session, by restoring the pre-fix shape under the new
  cases: `TestLedgerIntentsRefusesASubtaskThatIsNotThisTasksOwn` fails with
  `a subtask that is not this task's own must be refused, got [{"accepted":true,"user_seq":2,"seq":2}]`
  for all three shapes (`user_seq` 2, 3 and 4), and `TestLedgerIntentsRefusesABodyThatIsNotAList` fails
  with `POST /api/v2/ledger/intents body null = 200, want 422: []`. The `null` case is the reviewer's
  `[INFERENCE]` CONFIRMED through the route rather than argued.
- The green run's own observations: `an unknown subtask -> [{"rejected":true,"reason":"unknown_subtask","task_seq":0}]`,
  the same answer for another user's subtask and for a subtask of a different task, and
  `the accepted subtask: [{"accepted":true,"user_seq":1,"seq":1}]` as the FALSIFICATION — a route that
  refused every `subtask_id` would fail that line, and the row was read back to prove it carries the id
  the intent named.
- `gofmt -l` on the touched files prints nothing; `go build ./...` rc 0; `go vet ./...` clean.
- `go test -count=1 ./fastmcp/ledger/... ./fastmcp/server/routes/... ./fastmcp/server/httpapp/... ./fastmcp/task_management/...`
  with `AGENTHUB_TEST_PG_URL` set: **every package ok, 0 FAIL**. The three packages this change touches were
  re-run with their summary read in full - `fastmcp/ledger/domain/entities` 0.002s, `fastmcp/server/routes`
  0.006s, `fastmcp/server/httpapp` 82.233s - and the whole `task_management/...` subtree came back ok in the
  same sweep.
- The database cases RAN rather than skipping, and their times say so: the two new cases
  (`TestLedgerIntentsRefusesASubtaskThatIsNotThisTasksOwn` 1.39s,
  `TestLedgerIntentsRefusesABodyThatIsNotAList` 1.46s) beside
  `TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder` 1.43s. A skipped case prints nothing without
  `-v` and reads exactly like a pass, which is why the times are here.
