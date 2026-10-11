# Fix migration 0003 subtask progress scoping

Date: 2026-10-11
Scope: `agenthub_go` migrations

## Summary
In migration `0003_progress_history_carry_and_drop.sql`, the carry insert and verification checks (`missing`, `unheld`, and `mismatched`) joined `progress_carry_entries` with `task_events` on `user_id`, `task_id`, `kind = 'progress'`, and `progress_number`. However, tasks and their subtasks often share the same `task_id` and have overlapping `progress_number` values (e.g. `1`), with their actual discrimination resting in `subtask_id` (`NULL` for parent tasks, non-NULL for subtasks).

Without `te.subtask_id IS NOT DISTINCT FROM e.subtask_id`, comparing a task note against a subtask note with the same progress number triggered a false-positive mismatch exception ("progress_number is held by a ledger event whose content differs... for 478 entries"). Adding `te.subtask_id IS NOT DISTINCT FROM e.subtask_id` guarantees identity parity across parent task and subtask progress notes.
