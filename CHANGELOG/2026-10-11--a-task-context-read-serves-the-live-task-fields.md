## A task context read serves the live task fields, not the copy the record was created with

### Fixed

**The task's own fields have one source again: the task entity, read at serve time.**
- `fastmcp/task_management/application/services/unified_context_service.go`: `GetContext` (and so
  `ResolveContext`) overlays the live task's own fields onto the served `task_data` of a task context —
  `status`, `priority`, `labels`, `assignees`, `created_at`, `updated_at` — and leaves everything the context
  owns (`objective`/`estimated_effort`, `progress`, `insights`, `next_steps`) as stored. A nil lookup, a lookup
  error, a task that no longer exists or a record without `task_data` keeps the stored copy instead of failing
  the read.
- `fastmcp/server/httpapp/context_entity_lookup.go`: the entity lookup the service already receives gains
  `TaskOwnedFields`, the one read the overlay needs; `factories.UnifiedContextEntityLookup` carries this
  adapter already, so no new wiring.
- `fastmcp/task_management/application/services/task_owned_fields.go` (new): `TaskOwnedFieldsFromTask` is the
  single builder of that shape, shared with the sync below, so a handle written into a record and a handle read
  from the task normalize the same way.
- WHY: `task_data` is written only by creation-shaped paths, so it held a creation-time copy of the task's own
  fields and a done task resolved as `todo`. Measured red-first rather than asserted: with the overlay call
  removed, the acceptance test fails with `served task_data.status = todo, want the live "done"`, and the same
  line for `in_progress`.

**The silent sync failures are reported instead of swallowed** (`task_context_sync_service.go`).
- `SyncTaskMetadata`, `SyncTaskStatus` and `SyncSubtaskCounts` returned `nil` on a `GetContext` error, on an
  unsuccessful read body and on a failed `UpdateContext`; each now returns the error.
- All three also read the stored record from the key `context_data`, which the Go `GetContext` never produces
  (it answers under `context`, and the response factory reads it from there too), so every sync wrote onto an
  empty base and never saw the record it was updating. They now read `context` and take the existing
  `metadata`/`objective` maps with them.
- The four call sites that discarded the result with `_ =` (`use_cases/update_task.go`,
  `use_cases/create_task.go`, `use_cases/complete_task.go` twice) report a failure with `log.Printf` instead.
  The update and the completion still do not fail on a sync, which is their recorded intent; the failure is no
  longer invisible, which is what let this defect live for hours behind an hourly staleness.

### Testing
- ADDED `application/services/unified_context_service_task_owned_test.go`: the acceptance for a `done` row AND
  an `in_progress` row through the real service, what the context owns surviving the overlay, the stored copy
  kept when the lookup is absent/erroring/empty, a non-task level untouched, and the shared builder's key set.
- UPDATED `application/services/task_context_sync_service_test.go`: the fake answers the shape the Go
  `GetContext` really answers with, its reads and writes can fail on purpose, and the ruled behaviour is pinned
  (an unsuccessful body, a read error and a refused update all reach the caller; a record that was read survives
  the sync).
- `agenthub_go`: `gofmt -l` empty on the touched trees; `go build ./...` rc 0; `go vet ./...` clean;
  `go test -count=1 ./fastmcp/task_management/...` and `./fastmcp/server/...` pass.
- NOT RUN, named: the full-suite sweep carries two failures outside this change — `rigspec`'s
  `TestRenderRoomRigCLI` fails on "Daemon did not respond" (an external precondition, named and not claimed as
  fixed), and `TestConnectorCapCountsCharactersNotBytes` failed once inside the sweep and passes alone. The
  PG-backed wire tests were skipped because `AGENTHUB_TEST_PG_URL` is not set in this seat's environment; that
  is where the adapter's real `repo.GetTask` call would be exercised end to end.
