# The two findings GATE c663cca2 left open: the subtask note reaches the ledger, and the note's number is read inside the transaction

Both are from the same verdict and they meet in one place - how a progress note is written - so they
land together: the subtask note forced a decision about where a note's text and number come from, and
that decision is the MINOR's fix.

## (2) MAJOR - a subtask progress note was accepted and dropped

`manage_subtask`'s update action REQUIRES `progress_notes` ("MANDATORY for update/complete" in the tool
description; the handler refuses anything under 10 characters at
`subtask_mcp_controller/handlers/crud_handler.go:152` and sets it at `:179`). The use case read that
field and wrote it NOWHERE: a note the caller was required to send reached no reader at all. It could
not be worse timed - O1c moved a note's home to the ledger in the same cycle, and
`UpdateSubtaskUseCase`'s own removed column writer said so in a comment ("It joins the ledger when the
subtask composition reaches one").

Fixed, in the shape the ledger already had for it:

- **`application/use_cases/update_subtask.go`**: the use case takes a `StatusLedger` (`WithLedger`) and,
  when the request carries a note, records it through `SaveProgress` - the subtask and its note in ONE
  transaction, because `task_events.task_id` has an FK to the parent task and an entry written beside a
  rolled-back save is an orphan. The entry belongs to the **parent task's** ledger and names the
  subtask in `subtask_id`, which is exactly how the 0003 carry wrote the notes it moved out of the
  dropped columns and how `RecordProgress` already documents a subtask note.
- **`application/facades/subtask_application_facade.go`**: `Ledger` is a field and `WithLedger` routes it
  to the one use case that writes notes (the fallback construction site takes it too). **`server/httpapp/subtask_wiring.go`** builds the ledger for the request's user and branch the same way the task facade does, so production is wired - the failure mode otherwise is a note that fails loudly rather than one that vanishes.
- **`domain/entities/task.go`**: `NewProgressEntry` is the ONE definition of a note's stored form (the
  numbered header the column carried, the number, the timestamp), because the ledger now builds entries
  for a task's own notes and its subtasks'. `update_subtask.go` touches the subtask (`TouchForProgress`
  is on the task entity; the subtask's `Touch("progress_update")`) so its `updated_at` advances and
  stamps the note, which is what the dropped column writer did.

Tests: `use_cases/subtask_progress_note_test.go` (the note reaches the ledger with the subtask named and
the header, none when there is no note, none for a blank note - a fake records the subtask id);
`facades/subtask_application_facade_test.go` (the WIRE: the composition root builds the facade with its
repositories already in hand, which builds the update use case there and then, and only afterwards calls
`WithLedger` - so a facade that kept the ledger to itself would drop every production note. Measured
red: with the prebuilt use case left unwired the case fails at `HandleManageSubtask(update): status
ledger is not wired`); `infrastructure/database/subtask_note_ledger_integration_test.go` (real
PostgreSQL, real repositories, the real recorder: one row, `subtask_id` set, number 1, and the task
dialog's own render carries the note).

**Measured red FIRST**, because the defect is a silent drop: with the note path mutated back to the
pre-fix behaviour both cases fail - `ledger writes = 0` and `the task's rendered notes do not carry the
subtask's note ...; render = ""`.

## (3) MINOR - the note's number was read before the transaction

`StatusLedger.NextProgressNumber` read the task's MAX+1 OUTSIDE the transaction and with no lock, while
the append path takes `pg_advisory_xact_lock(hashtext(user_id))` for its own sequences. Two writers
could read one tip and both write it. The number is not a label: content plus `progress_number` is the
identity `ProgressTextWith` merges copies by, so a shared number is a lost note.

Fixed by moving the read where the lock is:

- **`infrastructure/repositories/task_event_repository.go`**: `NextProgressNumberInTx` reads MAX+1
  inside the caller's transaction and takes the SAME user-keyed lock the append takes (one lock, both
  sequences - as `AppendInTx`'s own comment insists). Outside a transaction it refuses.
- **`application/use_cases/status_ledger.go`**: `recordNotes` assigns each note its number there and
  builds the entry; `LedgerProgress` therefore carries the note's TEXT and timestamp, not a pre-built
  entry. `NextProgressNumber` and its payload reader are deleted rather than left as a second,
  unlockable route.
- **`application/services/task_event_recorder.go`** delegates the read, so the use cases never touch the
  repository directly.
- The three call sites (`create_task.go`, `update_task.go`, `update_subtask.go`) build a raw note and
  `TouchForProgress` the entity; the seven ledger fakes gained the method.

Tests: `repositories/task_event_repository_test.go`'s new case against a real PostgreSQL - the read
refuses outside a transaction, continues a carried tip (a note numbered 7 gives 8), and two writers in
two transactions take {8, 9} rather than sharing one.

## Verified

- `go build ./...` rc 0; `go vet ./fastmcp/task_management/... ./fastmcp/server/httpapp/...` rc 0;
  `gofmt -l fastmcp/` empty.
- The affected packages, green: `application/use_cases`, `application/facades`, `application/services`,
  `domain/entities`, `interface/mcp_controllers/task_mcp_controller/...`,
  `server/mcptoolpath/progressdetails`, and - run separately, because they are the slow ones -
  `infrastructure/database` (168.4s), `infrastructure/repositories` (428.4s), `server/httpapp` (240.4s).

## Not done

- `ListAfter` (and so `Events`) does not SELECT `subtask_id`, so no READER can yet say which subtask
  wrote a note - the integration case asserts the column from the row for that reason. That is a
  separate read-side gap, not part of this write fix, and it is worth its own ticket: a subtask that
  renders its own notes needs it.
