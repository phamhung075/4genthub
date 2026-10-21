# The ledger records the context's version, and the sync stops writing fields the row cannot store

A task's context history was unreadable as a sequence and full of changes that never happened. Two defects,
measured on the writer.

**The version was always 0.** `UnifiedContextService.UpdateContext` read the saved row's version out of
`Metadata["version"]` with an `int` type assertion. The repository carries that column in the ROW's own type
(`*int64`, `task_context_repository.go`, the shape its own test pins), so the assertion never matched, `ver` stayed
at its zero value, and every `context_updated` entry of every task recorded `version: 0`. `contextVersionOf` reads
the three shapes the map can hold (`*int64` above all) and is the one place the ledger's number comes from.

**Phantom adds, once per task update.** `SyncTaskMetadata` copied the task's `status`, `priority`, `labels`,
`assignees`, `created_at` and `updated_at` into the context's `metadata`, and the context row has no column for any
of them - the task row is their home and a context read serves them from it (`TaskOwnedFieldsFromTask`). The write
was dropped by the repository, the next read composed the metadata without them, and `ContextChanges` therefore
reported `add metadata.status`, `add metadata.assignees`, ... on every update, forever. The fields are no longer
written; the context owns exactly one of the task's values, the objective's `estimated_effort`, and when that
value is unchanged the write is skipped entirely instead of bumping the version with an empty change set.

**The completion carried the same phantom under another name.** `SyncTaskStatus` - the other half of the pair
`complete_task` runs after it records the result - set `metadata.status` on the context and updated it, so every
completion still recorded `add metadata.status` after the sync above was fixed. The field is the task row's, and a
context read already serves it from there through the http app's context lookup, so the writer is deleted rather
than made harmless: the service method, the hook that built the facade for it, the `CompleteTaskHooks` method and
its one call site. `TestTaskContextSyncService_SyncKeepsTheExistingRecord` drives `SyncTaskMetadata` now and
asserts `status` is absent from the metadata it passes through while the record's own keys survive - the shape the
deleted `TestTaskContextSyncService_SyncTaskStatus` used to pin, inverted.

Verified: `go test ./...` in `agenthub_go`, 138 packages ok, 0 failed. New rows:
`TestTheLedgerRecordsTheContextRowVersion` drives the writer through the real recorder with the repository's own
`*int64` shape and asserts the entry's version (7); before the fix it recorded 0 by construction.
`TestTaskContextSyncService_SyncTaskMetadata` now asserts the task-owned keys are ABSENT from the write it still
makes, and `TestTaskContextSyncService_SyncTaskMetadataSkipsAnUnchangedObjective` asserts no write at all when the
objective already holds the value.
