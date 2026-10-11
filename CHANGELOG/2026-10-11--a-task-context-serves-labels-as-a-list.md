## A task context serves `labels` as a list, and the sync's comment matches its code

### Fixed

**`task_data.labels` is a list even when the task has no labels** (`application/services/task_owned_fields.go`).
- `TaskOwnedFieldsFromTask` served `task.Labels` raw, so a task carrying none answered JSON `null` where
  the entity's own reader says `[]` (`domain/entities/task.go:85-86` normalizes it) — two shapes out of
  one field, introduced by the builder that replaced the stored copy.
- `taskContextLabels` now serves the entity's shape, next to `taskAssigneeHandles`, which is what makes
  the pair read as one rule: the builder serves each field the way the task's own field is shaped.
- `assignees` is untouched.

**The `SyncSubtaskCounts` comment states what the code does** (`application/services/task_context_sync_service.go`).
- It still claimed "Python swallows all exceptions, so failures return nil". That was the defect the
  previous change removed. What remains true is narrower and now written down: the function's own
  preconditions (an unusable task id, an absent or unusable subtask repository, a failed subtask read)
  return nil, while its context read and its update return errors to the caller.

WHY THE LABEL SHAPE MATTERS, measured rather than asserted: the red-first run below shows the served
value as `[]string(nil)` before the fix.

### Testing
- ADDED one assertion to `application/services/unified_context_service_task_owned_test.go`
  (`TestTaskOwnedFieldsFromTask`): a task with no labels serves a non-nil empty list.
- RED FIRST, by overlay rather than by assertion: with only `taskContextLabels(task.Labels)` reverted to
  `task.Labels` in a `/tmp` copy overlaid with `go test -overlay`, the case fails with
  `labels for a task with none = []string(nil), want a non-nil empty list`. No repo file carried the
  experiment.
- `agenthub_go`: `gofmt -l` empty on the three touched files; `go build ./...` rc 0; `go vet
  ./fastmcp/task_management/...` clean; `go test -count=1 ./fastmcp/task_management/application/services`
  passes for `TestTaskOwnedFieldsFromTask`, `TestZucs*` and `TestTaskContextSyncService*`.
- NOT RUN, unchanged and named: the PG-backed packages skip without `AGENTHUB_TEST_PG_URL`, so the
  adapter's real `repo.GetTask` read is still covered only at unit and route level.
