# The task-context create stops copying the task's own fields into `task_data.metadata`

## Changed

- `fastmcp/task_management/application/services/task_context_sync_service.go`: `SyncContextAndGetTask` no
  longer writes `task_data.metadata` from `TaskOwnedFieldsFromTask`. Those fields - status, priority,
  labels, assignees, `created_at`, `updated_at` - have ONE home: the task's columns, which the context read
  overlay serves as the entity's `Metadata`. Nothing read the copy: the write path reads none of those
  keys, and a second home is a place two writers can disagree. The create still writes `task_data` and the
  objective's `estimated_effort` in the same ONE `UpdateContext`, so the ledger still appends exactly one
  `context_updated` event per create (hub task 26e857b0). The comment above the write said the opposite and
  is corrected to say what the code now does.
- `fastmcp/task_management/infrastructure/repositories/task_context_repository.go`: `taskContextRepoToEntity`
  drops `metadata` from `task_data` alongside `progress`, `insights` and `next_steps`. A row written before
  the copy was removed is not migrated - the key is ignored on read, exactly as an absent one would be.

## Tested

- `go test ./...` in `agenthub_go` -> ok.
- `TestOneCreatePathWriteAppendsOneTaskContextEvent` now also asserts the one create-path write carries no
  `metadata` key under `task_data`, so the count cannot be satisfied by keeping the copy and dropping
  something else.
- `TestTaskDataMetadataCopyIsNotServedBack` (new, `internal/repositories`) drives `taskContextRepoToEntity`
  with a row whose `task_data` still holds the old copy: the copy is not served back, `task_data` itself
  survives, and `Metadata` keeps its column-derived keys (`version` present, `status` absent).
- `go test ./fastmcp/task_management/... ./fastmcp/server/httpapp/...` -> ok.
