# 2026-10-11 — O1c 3b reversed: 06410692 is landed, additively

### Changed
- `ai_docs/core-architecture/agenthub-system-architecture.md` and `agenthub_go/NEXT_GEN.md` (D1 3b, board row `ea98a7e3`). `af7d3345` ruled `06410692` superseded; that ruling is reversed to LAND, additively. `SubtaskDTO.details` is a joined rendering, the same shape as `TaskDTO.details`, and 3a already says a rendering is not a second store. The O1c carry re-sources both from `progress` events. The open point for the one-timeline commit is recorded: deleting `ProgressHistoryTimeline` removes the renderer of the subtask's `details`.

### Verified
- The architect read:
  - at `python-backend-final`, `Subtask.to_dict` (`subtask.py:540-541`) serves raw history and no `details`, and `task_response.py:23` has `details` on tasks only;
  - `task_event_routes.go:47-61` emits no `subtask_id`;
  - `b75c6afd` (the parent of `06410692`) is an ancestor of HEAD.
- Docs only; no code or tests changed.
