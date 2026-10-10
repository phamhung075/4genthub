## One key for one idea in the context entity

Lead item 3 of 3 from the MCP-path reading (`qitem-20261010184231-f2dc16b04d6a42b2`): the same
progress note had two homes under two names in one entity. Aligned on the name that survives.

### Fixed
- `agenthub_go/fastmcp/task_management/domain/entities/context.go`, `TaskContextUnified.UpdateProgress`:
  the method wrote the same event **twice, under two names, into two maps** — a transition record into
  `Metadata["progress_history"]` and a note-only record into `ImplementationNotes["progress_updates"]`,
  the second only when `notes` was non-empty. It now writes **one entry, into `progress_updates` only**,
  carrying the whole transition (`old_progress`, `new_progress`, `notes`, `timestamp`) so nothing the
  retired write carried is lost, and the entry is written on every accepted change rather than being
  silently skipped when there is no note.

### Why `progress_updates` is the survivor
- It is the key the **live** path writes and reads: `UnifiedContextService.AddProgress`
  (`application/services/unified_context_service.go:566-577`) appends to `progress_updates`.
- `progress_history` is the **retired** name. Grepping the module, nothing read either key except the
  writers themselves (four sites, two of them in this one method), so the choice is not driven by a
  consumer that would break — it is driven by which name the live path already uses and by the name
  collision with the task column that the ledger cutover removes.
- `TaskContextUnified.UpdateProgress` has **no non-test caller** in the module (its only reference is
  `context_test.go`). That is reported rather than acted on: removing a ported domain API surface is a
  separate decision from aligning its key.

### Verified
- `go vet ./fastmcp/task_management/domain/entities/...` → clean; `go test ./fastmcp/task_management/domain/entities/...` → ok.
- **Fails before, passes after, executed rather than asserted**: in a detached worktree at HEAD
  (`d8bc319e`) with only the new test file copied in, `go test -run TestTaskContextUnified` fails at
  `context_test.go:117` — *"progress_history is the retired name and must not be written"* — because HEAD
  still writes the retired key twice. In the working tree the same test passes.

### Open, stated rather than silently settled
- The live path writes `progress_updates` at the **top level** of the context dict, while this entity
  writes it **inside `implementation_notes`** — one name, two locations, and the two writers therefore
  never see each other's entries. Unifying the **location** changes the shape the running service stores
  (`UnifiedContextService.AddProgress`), which is a live-path change and is the lead's to rule on. This
  change aligns the name, which is what the item asked for, and does not touch the live path.
