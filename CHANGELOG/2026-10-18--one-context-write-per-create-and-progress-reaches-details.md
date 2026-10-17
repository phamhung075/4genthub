# Two task-progress defects closed: one context write per create, and add_progress reaches Details

Date: 2026-10-18. Hub tasks `26e857b0` (duplicate context_updated on create) and `4138904d`
(add_progress never reaches the board item), queue rows `qitem-20261017221351-51976b1ea6db` and
`qitem-20261017221351-09db6be5b5e5`.

## Measured first, on the running server

A create appended TWO `context_updated` events for the same task (`400f9a29…`, seq 1 and 2, both
`{"level":"task","version":0.0}`). A temporary stack print at the one append site
(`unified_context_service.go:457`) named both callers in one create:

1. `CreateTaskUseCase.autoCreateTaskContext` → `TaskHooks.SyncTaskMetadata` →
   `TaskContextSyncService.SyncTaskMetadata` → `facade.UpdateContext` (`task_context_sync_service.go:331`);
2. `TaskApplicationFacade.CreateTask` → `SyncContextAndGetTask`
   (`task_context_sync_service.go:169`) → `facade.UpdateContext`.

## What changed

- **`create_task.go`**: `autoCreateTaskContext` no longer calls `SyncTaskMetadata`. Creating a context
  is not an update; the request's single task-context writer is `SyncContextAndGetTask`, which now
  runs once per create. `CreateTaskHooks` therefore no longer embeds `TaskEventHooks` — it declares
  the two side effects it uses (`CreateTaskContext`, `NotifyTaskEvent`).
- **`task_context_sync_service.go`**: `SyncContextAndGetTask`'s one write carries the union the two
  writes used to split — `task_data`, `metadata` (`TaskOwnedFieldsFromTask`) and `objective`
  (`estimated_effort`).
- **`unified_context_service.go` `AddProgress`**: a task-level note now also appends the task's
  `progress` ledger event, with `content` in the payload. A task's details ARE its `progress` events
  (`Task.ProgressTextWith`), so this is what makes `manage_context add_progress` and
  `manage_task update details` one visible surface.

## Proof

- Unit (`application/services`, new file): `TestOneCreatePathWriteAppendsOneTaskContextEvent` drives
  the real `UnifiedContextService` + `TaskContextSyncService` and asserts exactly one append and that
  the write carries `title`, `assignees` and `estimated_effort`; `TestAddProgressReachesTheTaskLedger`
  asserts one `progress` event carrying the note, and that `ProgressTextWith` renders it.
  `TestCreateTaskUseCaseHooksSetContextIDAndNotify` now expects the hook sequence `[context notify]`.
- On the running server against scratch Postgres (same build, `AUTH_ENABLED=true`):
  `manage_task create` → `context_updated=1` (was 2); `manage_context add_progress` on that task →
  `manage_task get` … `details` ends with `ADD_PROGRESS note visible on the board`.
- `go test ./fastmcp/task_management/... -count=1`: all packages ok; `go vet` clean; `go build ./...`
  clean.
