## The status write and its `status_changed` event are one transaction

### Changed

- `agenthub_go/fastmcp/task_management/application/use_cases/status_ledger.go` (new) — `StatusLedger{Tx, Ledger}` and `SaveStatus`: one transaction, the row's status read before the save and again after it, and the entry written with those two values. Left unwired, a use case saves exactly as it did before, which is what left every other caller and every other test unchanged.
- `.../use_cases/update_task.go` and `.../use_cases/complete_task.go` — `WithLedger`, and every status write routed through `SaveStatus`. Completion writes three (the task's `in_progress`, then `done`, and the dependent task's `blocked -> todo`), each carrying its own entry in its own transaction.
- `.../application/services/task_event_recorder.go` — `RecordStatusChange` writes the entry for one transition with the payload `{old, new}` and the acting user, or the system actor when the path cannot name one.
- `.../infrastructure/repositories/task_event_repository.go` — `AppendInTx` and `StatusOf` REFUSE a context carrying no transaction, so an entry can never be committed beside the status it describes; the sequence is assigned under a per-task advisory lock inside that transaction.
- `.../infrastructure/database/session_manager.go` — the transaction runner the ledger takes.
- `agenthub_go/fastmcp/server/httpapp/task_wiring.go` — the composition root builds one ledger per facade and wires it into both use cases the MCP handler and the REST route reach, so both surfaces get the behaviour through the same objects rather than two parallel paths.
- Three new tests, one per write path (below), and `NEXT_GEN.md`'s O1b line with `TEST-CHANGELOG.md`.

### Why one transaction

The parity the ledger's reader relies on — a task's last `status_changed.new` equals `tasks.status` — holds only if the entry describes what the row actually committed. Reading the status inside the write's own transaction, before and after the save, makes `old` and `new` the row's values rather than a caller's memory of them, and makes a failure on either side roll both back.

### Testing

From `agenthub_go` with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`, against a throwaway PostgreSQL (`bash tools/testpg/start.sh`, port 55432):

- `go build ./...` ok; `go vet ./fastmcp/task_management/... ./fastmcp/server/httpapp/` clean.
- `go test -count=1 ./fastmcp/task_management/application/use_cases/ ./fastmcp/task_management/application/services/ ./fastmcp/task_management/application/facades/ ./fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/ ./fastmcp/task_management/infrastructure/repositories/` → all ok (repositories 51.999s; the database-gated cases RAN rather than skipping).
- `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 ./fastmcp/server/httpapp/` → `ok 18.975s`.
- **Observed, read from the test output rather than asserted from intent**: `update_task` `before="todo" after="in_progress"` with exactly one entry and one transaction; `complete_task` entries `[todo in_progress]`, `[in_progress done]`, `[blocked todo]`; the MCP path (`crud_handler.UpdateTask` -> the real facade -> the real use case -> the ledger) `before="todo" after="in_progress"` with one entry; and `PUT /api/v2/tasks/{id}` -> `200` with entries `[[todo in_progress]]`.
- **RED FIRST, measured**: with the ledger left unwired the same cases fail `entries = 0 ([]), want exactly 1` and `entries = [], want [...]`, and the test files cannot compile against the pre-change tree at all, because they name the new API.
- **The two claims a fake cannot make, on the real database**: the parity query (each task's last `status_changed.payload->>'new'` against `tasks.status`) returns **0** rows; and with a trigger refusing every `task_events` insert, the route reports failure, `tasks.status` stays `in_progress`, and the committed set of entries is unchanged — which holds only if the status write and its entry share one transaction.
- Without `AGENTHUB_TEST_PG_URL` the `httpapp` case skips loudly, in the same form as its package neighbours.

### Two things recorded rather than changed

- The REST task route reports ANY update failure as `404 {"detail":"Task not found"}`. That is why the forced-failure observation reads as a 404 instead of the ledger's own error. It is outside this row and is not touched here.
- A seeding note for anyone extending the database case: the composition scopes repositories by `domain.ValidateUserID`'s mapping of the user id (a uuid5 of the token subject), not the subject verbatim, so a row seeded with the subject yields `Task ... not found` and no entry. The root cause is the mapping, not the ledger.

### Not covered

The unit-level fakes cannot show atomicity, so neither unit file claims it; both say so in their headers. O1b's verdict is outstanding, and the change exactly as verified is kept at `FIX-o1b-status-ledger-HELD-2026-10-10.diff`.
