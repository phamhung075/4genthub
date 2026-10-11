# Fix migration 0003 subtask progress scoping

Date: 2026-10-11
Scope: `agenthub_go` migrations

## Summary
In migration `0003_progress_history_carry_and_drop.sql`, the carry insert and verification checks (`missing`, `unheld`, and `mismatched`) joined `progress_carry_entries` with `task_events` on `user_id`, `task_id`, `kind = 'progress'`, and `progress_number`. However, a subtask ALWAYS carries its parent's `task_id` - `subtasks.task_id` is `NOT NULL` with `FOREIGN KEY (task_id) REFERENCES tasks(id)` in `0001_baseline` - and each side numbers its own notes from 1, so the SAME `progress_number` on both sides is the norm rather than an overlap to hope for. What tells the two rows apart is `subtask_id` (`NULL` on a task-attributed event, non-NULL on a subtask's).

Without `te.subtask_id IS NOT DISTINCT FROM e.subtask_id`, comparing a task note against a subtask note with the same progress number triggered a false-positive mismatch exception (`progress_number is held by a ledger event whose content differs from the column's, for N entr(ies)`). Adding `te.subtask_id IS NOT DISTINCT FROM e.subtask_id` guarantees identity parity across parent task and subtask progress notes.

## The count this entry first quoted is unsourced, and its unit is joined rows

This entry first quoted the exception as firing "for 478 entries". Both halves of that are wrong to state.

- **UNSOURCED, and not reproducible from this repository.** No database reachable from the rig carries that data - the retroactive gate's verdict probed every database it could reach, including a copy of the cluster, and found 0 rows - so the figure came from the environment the fix was written in rather than from a measurement anyone here can re-run. Read it as a number to source or drop, not as evidence.
- **The message's unit is JOINED ROWS, not entries.** `mismatched` is `count(*)` over a JOIN of `progress_carry_entries` to `task_events` (`0003_progress_history_carry_and_drop.sql:177`) while the message prints `% entr(ies)` (`:189`), so one entry can be counted once per matching event and a count of 478 may be pairs rather than entries.

The predicate itself is now pinned by two cases at a SHARED `progress_number`, red on the parent revision and green here: `TestTheRuledCarryStepCarriesBothIdentitiesAtASharedProgressNumber` (different content, where the parent raises the collision) and `TestTheRuledCarryStepCarriesTheSubtaskNoteTheLedgerAlreadyHoldsForTheTask` (the ledger already holds the task's event for the note, where the parent reports the entry as held and drops the subtask's note silently), both in `progress_history_drop_integration_test.go`.
