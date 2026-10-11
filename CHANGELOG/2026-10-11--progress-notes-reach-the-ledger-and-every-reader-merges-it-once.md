## Progress notes reach the ledger, and every reader merges the two sources once

### The decision behind it

The architect's O1c ruling removes `progress_history` **with carry**, and the carry is where the drop is
built. The lead's decision for this half (row `qitem-20261011040203`, which supersedes an earlier
accept-the-switch message that crossed it in flight) is therefore a **DUAL WRITE**: the column keeps
holding every note while the ledger starts holding them too, because the column is what every reader that
has not been re-pointed still reads, and because it keeps `ProgressCount` the ONE number source - there is
no "1 + max across two sources" rule to get wrong.

The price of a dual write is stated where it is paid: a note then exists in BOTH sources, so a reader that
concatenates the two renders it twice. The identity that collapses them is the one the payload itself
declares - `{content, progress_number}` for a live note, with a carried note recognized by its
`carried_from` - never a heuristic reconstructed from a timestamp or a sequence.

### Changed

- `agenthub_go/fastmcp/task_management/domain/entities/task.go`: `Task.AppendProgress` still writes the
  column and now **returns** the note it numbered, as `ProgressEntry` (content with its numbered header,
  number, timestamp, storage key), so the caller can record the same note as a ledger entry without
  reimplementing the header or the counter. `ProgressEntries()` exposes the column's entries in the order
  `GetProgressHistoryText` joins them, which is what lets a merge sort both sources by one rule; and
  `ProgressTextWith(events)` is the merge itself, ordered by number, joined exactly as the column's own
  rendering was - so a reader that passes no events sees precisely what it saw before.
- `agenthub_go/fastmcp/task_management/application/services/task_event_recorder.go`: `RecordProgress`,
  **additive** - `Record` and `RecordStatusChange` are untouched, so every existing caller keeps the shape
  it was written against. It carries the note's content, number and timestamp, and the subtask id when the
  note is a subtask's, because an entry belongs to the TASK's ledger (`task_events.task_id` has an FK to
  `tasks.id`) and `subtask_id` is what says which subtask wrote it.
- `agenthub_go/fastmcp/task_management/application/use_cases/status_ledger.go`: the seam that owns the
  transaction now carries the notes, because a progress entry has to share a transaction with the save it
  describes. `Save` records the status transition AND the progress entries; `SaveProgress` is the
  notes-only half, for the create path, which has no transition to record and no row to read a status from
  before the save. `Events` reads the ledger back, so an update's own response carries the note it just
  wrote. Entries are written AFTER the save: an entry written before the row it points at exists cannot be
  inserted, and one written outside the transaction could commit beside a save that rolled back.
- `agenthub_go/fastmcp/task_management/application/use_cases/update_task.go` and `create_task.go` switched
  end to end; `complete_task.go`'s three call sites moved to the seam with no notes; `get_task.go` reads
  the ledger through a lister and `TaskResponseFromDomain` takes the events, so the merge happens in one
  place for both the response builder and the websocket payload builder.
- `agenthub_go/fastmcp/server/httpapp/task_wiring.go`: ONE `TaskEventRepository` is now the ledger's read
  and write side - the recorder writes through it, the update response reads its own note back through it,
  `GetTask` merges it, and the resume brief uses the same one.

### Not switched, and why

- **The subtask site.** `UpdateSubtaskUseCase` is built by `SubtaskApplicationFacade`, which has no ledger
  in reach. The seam refuses rather than dropping a note (`ErrLedgerNotWired`), so switching there would
  break a live path; `Subtask.AppendProgress` is unchanged and its doc says so. The subtask history has ONE
  source, so it cannot render twice, and it joins the ledger when the subtask composition reaches one. The
  subtask's own `details` are the separate item the ruling already names (`06410692`, off-branch).
- **`context_routes.go:211`** was named as a fourth site by a reconnaissance and repeated to me as one. No
  such caller exists: `AppendProgress(` has exactly three non-test callers (`update_task`, `create_task`,
  `update_subtask`), and `fastmcp/server` contains no `AppendProgress` or `progress_history` reference at
  all - that route's `AddProgress` returns 501. There was nothing to switch.

### Tests

`TestProgressTextWithRendersANoteOnceWhenBothSourcesHoldIt` is the lead's sentence for this commit made
checkable: the same note held by both sources renders once, in order, from one read. Its parts each close a
way the merge could be wrong - the ledger's copies arrive out of order (so order comes from the number, not
the slice), one is the carry's copy of a column note (`carried_from`), one note exists only in the ledger,
a `claimed` event with progress-shaped fields proves the kind filter, and a nil slice must leave exactly the
column's own text. The existing `AppendProgress` assertion now also pins the handed-over note object.

### Verified

- `gofmt -l` on the ten touched non-test files: empty.
- `go build ./...` rc 0.
- `go vet ./...` clean.
- `go test -count=1 ./fastmcp/task_management/...` -> every package `ok`.
- `go test ./... -count=1` -> every package `ok`, no `FAIL` line anywhere in the run.
- NOT PROVEN HERE, named: the `AGENTHUB_TEST_PG_URL`-gated cases need a live cluster and are not part of
  what these runs proved; and no case yet proves the entry reaches the database, because that needs the
  same cluster. What the fakes prove is the call path and the merge.

### Found by

The lead's O1c code half (`qitem-20261010181501`), decided in `qitem-20261011040203`; the site map that
established there was no ensurer, migration or ALTER for these columns - and so no way for the code to drop
them - is recorded at `4genthub-min/O1C-REMOVAL-SITE-MAP-2026-10-11.md`.
