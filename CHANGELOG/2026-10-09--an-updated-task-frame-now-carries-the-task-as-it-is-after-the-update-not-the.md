## An 'updated' task frame now carries the task as it is AFTER the update, not the row the update replaced

### Fixed
- `agenthub_go/fastmcp/task_management/application/facades/task_application_facade.go` — the `updated` broadcast built its payload from `current`, the PRE-update fetch that `checkForMeaningfulUpdate` compares against. Status, title and priority were therefore the values the task had *before* the change while `updated_at` came from the new row, and the client writes this dict straight into the task it displays — so once delivery was fixed, a status change would have arrived carrying the old status. The payload now comes from the response's own dict (the post-update row); `current` keeps its single purpose, the meaningful-change comparison.
- Inherited, not a port slip, and worth saying: the Python original's own comment claims `current_task` has all fields, and it built the payload the same way.

### Verified
- **SEEN RED FIRST:** `TestTheUpdateBroadcastCarriesThePostUpdateValues` failed on the parent with `the delivered payload carries status "todo", want the post-update "in_progress"` — and that red is only possible because the repository fake serves a fresh copy per read; one shared pointer would have let the pre-update snapshot carry the use case's mutation and pass for the wrong reason.
- `go test -count=1 ./fastmcp/task_management/application/facades/` → **ok**; `go vet` clean; `gofmt -l` prints nothing.
