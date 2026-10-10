## A board write reported success while the read returned nothing: the decode boundary put a foreign container in the field

### The defect
`manage_task action=update` with a `details` string answered SUCCESS and echoed the note in its own reply, while `manage_task action=get` on the SAME row returned `details` as two empty entries joined by the separator - `"\n\n"`. On row 87c58552 that looked like two seats' progress notes being lost, and the consequence is why the row is high: a seat that records progress only in `details` records nothing.

### What was NOT wrong, established before touching anything
- The write path: `update_task.go:102-103` does call `entity.AppendProgress`, and the stored column held BOTH notes with their contents intact (measured in the red run below). The write was never the fault.
- The keys: `AppendProgress` (`domain/entities/task.go:290`) stores `content` plus `progress_number`, and `GetProgressHistoryText` (`:497-498`) reads exactly those. They agree.
- The context carrier: `manage_context action=add_progress` writes the context row's `implementation_notes.progress_updates` - a separate carrier that was already green, before and after this fix.
- The ticket's premise that a dedicated progress action exists is REFUTED: `manage_task action=add_progress` answers `UNKNOWN_OPERATION`. The case asserting that absence stays in the test, so the absence is measured rather than assumed.

### The cause, in one line
`taskRepoDecodeHistory` (`infrastructure/repositories/task_repository.go:231`) turned `DecodeJSON`'s result into `map[string]any` at the TOP level only (`out[key] = value`, line 246 pre-fix), so each progress ENTRY stayed `*entities.OrderedMap[any]` - the container `ordered_json.go:16-19` documents for a JSON object. The reader then ran

    m, _ := v.(map[string]any)      // v is *entities.OrderedMap[any] -> m is nil, ok discarded
    c, _ := m["content"].(string)   // indexing a nil map, ok discarded -> ""

Both `ok`s are discarded, so an entry the reader could not type-assert was silently skipped instead of reported.

### The fix
`repoPlainValue` (`task_repository.go:196-229`) replaces `*entities.OrderedMap[any]` with `map[string]any` recursively, and the two history decoders use it: `taskRepoDecodeHistory` (`:246`) and `subtaskRepoDecodeHistory` (`subtask_repository.go:710`). A JSON column decoded into a `map[string]any` field now carries the same container one level down that the entity's own writer and readers produce. No entry shape changed, no compatibility shim, no second mechanism: the write was already correct, so the decode boundary was the wrong layer and the fix belongs there. An orphaned `taskRepoDecodeHistory` doc comment that sat above `repoDecodeStringList` was re-attached to the function it describes.

### Red first, and the red is reproducible by anyone
`fastmcp/server/mcptoolpath/progressdetails/progress_details_tool_path_pg_test.go` drives the production wire (`POST /mcp`, `tools/call`) and asserts CONTENT, never that a call reported success. Against a clean pre-fix worktree at `5f8fad86` it FAILS on the first path exactly as the row describes:

    OBSERVED manage_task get details="\n\n"
    lost progress note 1: details="\n\n", want it to contain "wired the progress writer into the update path"
    lost progress note 2: details="\n\n", want it to contain "verified the round trip against the stored row"

and PASSES on this tree (3/3 subtests, 1.66s). The test owns its own package for a recorded reason rather than to dodge a package clause or an import cycle: `services.RepositoryProviderService.GetInstance` caches a provider built from the FIRST composition's repository backend (`repository_provider_service.go:63-73`) and `httpapp.NewApp` sets that backend (`app.go:40`), so one App composition per binary - the same reason `mcptoolpath/doc.go:4-7` records.

### The lost notes are NOT lost, and the ledger never had them
Measured: `tasks.progress_history` kept both contents intact, so the notes were UNREADABLE rather than deleted, and this fix surfaces them on the same row. Nothing was re-recorded. The forward-only answer is narrower than the ticket assumed and is an honest negative: `task_events` holds NOTHING for these notes. There is no production writer of kind `progress` at all - the only writers are `status_changed` (`application/use_cases/status_ledger.go:76`) and `evidence_submitted` (`server/httpapp/task_event_controller.go:94`); `TaskEventKindProgress` exists in the vocabulary, the CHECK constraint and tests only.

### Verified
- RED, mine, on a clean worktree at `5f8fad86` (quoted above); GREEN post-fix, 3/3 subtests, with `AGENTHUB_TEST_PG_URL`.
- `gofmt -l` empty on the touched files; `go vet` clean on the repositories and the new package; `go build ./...` rc 0.
- The shared decode boundary swept with the DSN: `go test -count=1 ./fastmcp/task_management/...` -> 68 packages ok, 0 FAIL, rc 0; `interface` and `httpapp` green (the latter 100.269s).

### One cross-item hazard, named rather than discovered later
O1c (`qitem-20261010181321`) is the destructive removal of `progress_history` and `progress_count` from the Go ORM, with the ledger replacing them. That is the very column this fix makes readable, and we have just measured that it still HOLDS live notes. So O1c must migrate or dump what the column carries as part of its recorded migration; this repair's decode path and its test go WITH the column when O1c lands, and neither should be read as a second mechanism.

### Found by
The board row `qitem-20261010224819` (two seats' notes never came back), reproduced red-first, and swept for regressions across the whole `task_management` tree.
