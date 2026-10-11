# The complete action writes the progress note its tool requires - and a completion with no ledger refuses instead of dropping it

The reviewer's re-gate finding on `cbf57aa7`, pre-existing and adjacent to the note fix that commit
landed: `manage_subtask` declares `progress_notes` REQUIRED for `complete` exactly as it does for
`update` (`tool_input_schemas.go:75`, `manage_subtask_description.go:28,30,38`), the router passed the
kwarg through, and the complete half then read four OTHER fields and dropped the note on the floor. The
update half had been fixed one layer at a time; the sibling was never touched, so the tool accepted a
required field and reported success without it ever being stored.

## What was wrong, at each layer

- **The router named a field the tool does not declare.** `ddd_compliant_mcp_tools_wiring.go`'s
  `CompleteSubtask` adapter read `kwOptString(kw, "completion_notes")` into the notes slot. No such
  property exists in the schema, so the value was always nil before the handler saw it. It now reads
  `progress_notes`, which is the field the tool and its description promise.
- **The handler enforced nothing.** `crud_handler.go` accepted a completion without a note, where the
  update half refuses a note shorter than 10 characters. It now applies the same rule, in the same
  place, with a completion-specific message (`Completions must include progress description.`), before
  the facade is called.
- **The use case had no note and no ledger seam.** `CompleteSubtaskUseCase.Execute` took seven
  arguments, none of them the note, and had no way to record one. It now takes the note and records it
  through the same `StatusLedger` seam `UpdateSubtaskUseCase` uses, inside the same transaction as the
  subtask's save: the entry goes to the **parent task's** ledger (`task_events.task_id` is the
  parent's, `subtask_id` names the writer), its content is the stored form with the `=== Progress N
  ===` prefix, its number is read inside the caller's transaction and its timestamp is the
  completion's own touched instant. O1c dropped the progress columns, so the ledger is the note's only
  home.
- **The facade wired the ledger into one use case of two.** `WithLedger` built the seam for
  `update_subtask` only, and both note-writing use cases are built in the facade **before** the
  composition root calls it - so the complete use case never held the ledger and had nothing to write
  with. `WithLedger` now wires both, and the branch that builds a complete use case on the fly (a
  facade built without repositories) carries the ledger too. Wiring one of the two is precisely how
  the other dropped its note silently.
- **The internal service path is unchanged, deliberately.** `SubtaskApplicationService.CompleteSubtask`
  is not a tool path and carries no note; it passes nil and writes nothing.

## The failure mode, named

A note that arrives with a completion and cannot be written is an ERROR, not a silent success: with no
ledger wired the use case returns `ErrLedgerNotWired` and saves nothing. Accepting the note and
dropping it is exactly the defect this packet fixes, so the path refuses rather than reproduce it.

## Verified

- `go test -count=1 ./fastmcp/task_management/application/use_cases/ ./fastmcp/task_management/application/facades/ ./fastmcp/task_management/application/services/ ./fastmcp/task_management/interface/...`
  -> 28 packages ok.
- MEASURED RED FIRST, one mutation per layer, because the defect was a SILENT drop:
  - the use case back to save-only (note accepted, never written): `ledger writes = 0, want 1: the note
    this completion REQUIRES reached no reader`, and the unwired-ledger case returns
    `err = <nil>, want ErrLedgerNotWired`. The no-note case stays green, which is the point of it.
  - `WithLedger` skipping the complete use case: `HandleManageSubtask(complete): status ledger is not
    wired: a status write must record its entry, and saving the status alone would be a silent success
    over a missing event`.
  - the handler's check removed: `op="complete_subtask" code="OPERATION_FAILED"` - the case passes a nil
    facade, so a handler that skips the rule reaches it and panics instead of passing quietly.
- `gofmt -l` clean on the touched files.
