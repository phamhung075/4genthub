# 2026-10-11 — O1c 3b: 06410692 is superseded, and the ledger is the only progress read path

### Changed
- `ai_docs/core-architecture/agenthub-system-architecture.md`: D1 sub-decision 3b (architect; board row `ea98a7e3`; lead qitem `9da64b7c`). `06410692` (the subtask's `progress_history` served as `details`) is superseded, not re-landed. 3a's sentence that go-dev re-lands it is corrected.
  - fe-dev now deletes the dead `fullSubtask.details` read at `SubtaskDetailsDialog.tsx:333-346`.
  - The task-dialog timeline swap waits on the carry, not on `06410692`.
- `agenthub_go/NEXT_GEN.md` (O1c box): the same correction.

### Verified
- The architect measured:
  - `task_event_routes.go:47-61` emits no `subtask_id`.
  - `TaskEventKindProgress` (`task_event.go:43`) has no writer.
  - `migrations/` holds `README.md` only.
  - `06410692` reads `progress_history` in `converters.go` and is not an ancestor of HEAD.
- Docs only; no code or tests changed.
