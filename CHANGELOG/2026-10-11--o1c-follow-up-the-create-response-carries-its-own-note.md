# O1c follow-up: the create response stopped carrying the note its own request wrote

Gate `c663cca2` returned REQUEST CHANGES with this as the BLOCKER, and it is the first finding rather
than the last because the tip was red: `go test -count=1 ./...` failed `application/use_cases`, both
cases on the same line shape - `details = ""`.

## What broke, and why the gate's reading is half of it

`c663cca2` moved progress notes out of the column and into the ledger, so `TaskResponse.Details` is now
rendered from the task's `progress` events by `ProgressTextWith`. The reviewer read the two failures as
stale assertions, on the evidence that production wires the seam (`server/httpapp/task_wiring.go`).
The wiring is real and the assertion was right: **`create_task.go` never called it.** At the parent it
built its response with

    task.TaskResponseFromDomain(ctx, taskEntity, u.gitBranchRepository, nil, nil, nil, nil, nil)

- `nil` for `progressEvents` - so with the column gone the create response came back one note short,
its own, while `update_task.go` already read the events back after the save and says why in a comment.
So the fix is the read-back the create path was missing, not an assertion changed to expect `""`; a
test rewritten that way would have passed while production kept dropping the note.

## Changed

- `application/use_cases/create_task.go`: after the save, read the task's ledger entries back (guarded
  on the seam and a non-empty id, exactly as `update_task.go` does) and hand them to the response
  builder, so `details` renders the note this request just wrote.
- `application/use_cases/status_ledger_progress_test.go` (new): the seam wired **and remembering**.
  `noopLedger` is a pass-through that records nothing - correct for the eleven cases about something
  else - so a case asserting the rendered note needs a seam that holds it: `RecordProgress` keeps the
  note the use case built and `Events` hands it back in the same payload shape the repository writes
  (`content` plus `progress_number`), which is the shape `ProgressTextWith` merges by.
- `application/use_cases/create_task_test.go`, `update_task_test.go`: the two cases that assert the
  rendered note run against that seam. The other nine keep `noopLedger`.

## Verified

- `go test -count=1 ./fastmcp/task_management/application/use_cases/` -> **ok 0.038s** (red before the
  fix: `create_task_test.go:112 details = ""`, `update_task_test.go:127 details = ""`).
- `gofmt -l` on the touched files: empty. `go build ./...`: rc 0.
- The gate's own point is recorded and taken: my MEASURED list for `c663cca2` named the packages I had
  reasoned about and omitted this one, and `go build` plus `go vet` at rc 0 cannot see a
  package-level behavioural break. The whole suite is the gate that could, and it is what found this.

## Still owed from the same verdict

Two findings remain open and are not answered here: the MAJOR (a mandatory subtask `progress_notes` is
accepted and dropped - `update_subtask.go` never reads it, and `StatusLedger.SaveProgress` already
names "writing a subtask note" as one of its two callers, so the seam exists and the caller is
unwired) and the MINOR (`NextProgressNumber` reads `MAX+1` before the transaction, where the append
path does its `MAX+1` under `pg_advisory_xact_lock`).
