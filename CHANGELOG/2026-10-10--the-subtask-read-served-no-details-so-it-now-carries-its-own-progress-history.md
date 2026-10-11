## The subtask read served no details, so it now carries its own progress history

### Changed
- `agenthub_go/fastmcp/types/entities.go`: `SubtaskDTO` gains `Details *string`, exposed by `ModelDump` as `dtoOpt("details", d.Details)` - the field name and the null-when-absent shape `TaskDTO` already serves (`task_response.go:140`, `:196`). Without it the subtask payload carried neither `details` nor `progress_history` nor `progress_count`, so neither subtask read could be repointed at served bytes and the live `4a0a8c7a` frontend fix had nothing to read.
- `agenthub_go/fastmcp/types/converters.go`: `SubtaskToDTO` fills `Details` from the subtask's OWN progress history in both branches (the repository's dict under `progress_history`, `pyGetattr` for an entity object). The new `subtaskDetails` helper returns nil when there is none, so the served value is null rather than "".
- `agenthub_go/fastmcp/task_management/domain/entities/task.go`: the join moved to the package-level `ProgressHistoryText(map[string]any) string`, and `Task.GetProgressHistoryText()` is now a one-line call of it. A task and a subtask write the same entry shape (`content` + `progress_number`: `Task.AppendProgress`, `Subtask.AppendProgress`), so the ordering rule has one implementation and the subtask DTO uses the same one the task response does.
- No column, no writer, no migration: `add_progress` is untouched, and no row is rewritten.

### Verified
- **FAIL-first, measured rather than argued from the diff.** With only `SubtaskToDTO`'s population removed (the field, the `ModelDump` entry and the new case left in place) `go test ./fastmcp/types/ -run TestSubtaskDTOservesDetailsFromItsOwnProgressHistory -count=1` -> `--- FAIL: ... dto_test.go:202: details = <nil>, want the joined history in progress-number order`. With the line restored the same command -> `ok agenthub/fastmcp/types`. The restored file was re-read to confirm the line is back.
- `gofmt -l fastmcp/types/ fastmcp/task_management/domain/entities/` prints nothing; `go vet ./...` rc 0; `go build ./...` rc 0.
- `go test ./fastmcp/types/... ./fastmcp/task_management/domain/entities/... ./fastmcp/task_management/interface/... ./internal/... -count=1` -> every package ok, including `internal/apiref`, which composes the tool registry.
- The route-level payload was NOT exercised: the subtask REST routes need `AGENTHUB_TEST_PG_URL`. The case pins the DTO those routes serialize (`SubtaskToDTO` -> `ModelDump`), not a live response, and the changelog says so rather than implying a route run.

### Found by
- Row `qitem-20261010210628-70049d83d61e016a` - the change fe-dev specified and the reviewer verified, taken ahead of the registry retirement because the `4a0a8c7a` fix was blocked on it.
