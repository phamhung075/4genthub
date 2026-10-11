# O1c addendum: list and search rows render their notes from the ledger

The gate on `c663cca2` found the list path last and it is the third finding, not the least:
`task_list_response.go` still passed `nil` for `progressEvents`, so every list and search row emitted
`details: ""` where the parent emitted the rendered notes. A field that is present and always empty is
indistinguishable from "this task has no notes", which is why it cannot stay.

## Fixed, in the shape that makes the field right

- **`application/dtos/task/task_list_response.go`**: `TaskProgressEventsByTask` is the batch seam
  (`ProgressEventsByTask(ctx, taskIDs)`), and `TaskListResponseFromDomainList` reads the page's notes
  **once** for the whole page - the same shape as the subtask counts beside it, and for the same
  reason - then hands each row its own events. The read is guarded on the seam and a non-empty id list,
  so a builder without a ledger still works.
- **`infrastructure/repositories/task_event_repository.go`**: `ProgressEventsByTask` is the one query:
  `kind = 'progress'`, scoped to the repository's `user_id`, `task_id IN (…)`, ordered by task and
  `seq`, grouped into a map. One page, one query - not a read per row.
- **Wiring**: `list_tasks.go` and `search_tasks.go` take the seam and pass it through; the facade's
  `deps` gains `ProgressEvents` (the same repository the resume brief already reads); `task_wiring.go`
  hands `taskEvents` to both.

## Why batched rather than per-row, measured against the reach

The reviewer's addendum traced what consumes a list item's `details` today: a row renders
`progressHistory={fullTask?.details}` with no fallback to the summary
(`TaskRowDesktop.tsx:107`, `TaskRowMobile.tsx:70`), and `fullTask` is filled only by `loadFullTask`,
which only `getTask` calls - so an unexpanded row behaves at the tip as it did at the parent. The
regression is real but narrow, and the honest trade is the batch reader: one query per page is the
shape that makes the field correct for any client, while a read per row for a field nothing currently
consumes would be cost for nothing. The third option - dropping `details` from list items explicitly -
is the one behaviour this cannot have, because the wire shape would then differ between two clients
asking the same question.

## Tests

- `dtos/task/task_test.go`: `TestTaskListResponseFromDomainList` now builds a two-task page, gives one
  task a note, and asserts (a) that row's `details` is the ledger's render, (b) the other row's is
  empty, and (c) the reader was called **once** with both ids. The fake records its arguments, so a
  per-row read would fail the third assertion rather than pass quietly.
- `infrastructure/repositories/task_event_repository_test.go` (new case,
  `TestProgressEventsByTaskIsOneReadForTheWholePage`): against a real PostgreSQL - two tasks, one with
  two notes and a non-progress event, another user's task in the same request; asserts grouping by task
  id, that only the `progress` kind comes back, `seq` order, no entry for a task with no notes, nothing
  from the other user, and an empty map (no error) for an empty page.

## Verified

- `AGENTHUB_TEST_PG_URL=… go test -count=1 -run TestProgressEventsByTaskIsOneReadForTheWholePage -v
  ./fastmcp/task_management/infrastructure/repositories/` -> **PASS (1.89s)**.
- `go test -count=1 ./fastmcp/task_management/application/dtos/task/
  ./fastmcp/task_management/application/use_cases/ ./fastmcp/task_management/application/facades/` ->
  **ok / ok / ok**.
- `gofmt -l` over `fastmcp/`: empty. `go build ./...`: rc 0. `go vet` on the touched packages: rc 0.
- `port_draft_use_cases_test.go`'s constructor call gained the third argument (`nil` - that case is
  about the filters, not the notes).

## Still open from the same verdict

Both other findings stand and are not touched here: the MAJOR (a mandatory subtask `progress_notes` is
accepted and dropped - `update_subtask.go` never reads it while `StatusLedger.SaveProgress` already
names that caller) and the MINOR (`NextProgressNumber` reads `MAX+1` outside the transaction where the
append path takes `pg_advisory_xact_lock`). The gate's own MINOR on the create read-back's error path
(a read failure after the row is committed fails a create that already happened) is recorded and also
untouched.
