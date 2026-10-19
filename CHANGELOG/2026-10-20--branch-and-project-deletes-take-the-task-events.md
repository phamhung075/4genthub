# INT-03 residual: the branch delete takes the task-event ledger with it

`task_events.task_id` is the one foreign key into `tasks` with no `ON DELETE CASCADE`
(`task_event_tables.go`: the application layer cascades by design). The task delete already
deletes its ledger (`task_repository.go`), but `ORMGitBranchRepository.DeleteBranch`
(`git_branch_repository.go`) removed tasks without it, so a branch whose task had any event row
aborted with SQLSTATE 23503 instead of deleting.

The branch delete is the one place to fix: the project delete path is not a second delete body -
`project_management_service.go` deletes each of the project's branches through `DeleteBranch` and
only then the project row, so by the time the project row goes there are no tasks left to block it.

- The per-task group (steps 5-9) now ends with step 10, `task_events` by the branch's task ids,
  before step 13 deletes the tasks. Later steps are renumbered 11-15; no other statement changed.
- Step 10 carries no user condition, unlike the steps above: `task_events.user_id` is the event's
  AUTHOR, not the task's owner, so an event another user wrote on this task would survive a
  filtered delete and still block the branch. The task delete precedent carries no filter either.
- The same author-versus-owner reading applies to every child the schema does NOT cascade, so the
  branch delete no longer filters ANY of them by `user_id`: task ids and branch-context ids are
  selected unfiltered (steps 3-4), and the deletes of `task_labels` (7), `task_contexts`
  (9, 11, 12), `tasks` (13) and `branch_contexts` (14) lost their `gitBranchRepoUserCond`.
  Branch ownership is still checked once, at the project (the guard at the top of `DeleteBranch`).
  The steps that keep the condition (`context_inheritance_cache`, `context_delegations`) hold
  tables with no foreign key into the branch, and the ones on `subtasks`, `task_assignees` and
  `task_dependencies` are cascade rows the database would take anyway - none can block.
- `project_repository.go` is untouched.

Tests (both red at `76b0d84d` with
`ERROR: update or delete on table "tasks" violates foreign key constraint "task_events_task_id_fkey" (SQLSTATE 23503)`,
green after the change):

- `TestGitBranchRepoDeleteBranchRemovesTaskEvents` seeds a branch task and one event through
  `TaskEventRepository.Append`, deletes the branch, and counts `task_events` by `task_id`.
- `TestGitBranchRepoDeleteBranchCascade` now also seeds children WRITTEN BY ANOTHER USER on every
  table that can block a branch delete (`task_labels`, `branch_contexts`, `task_contexts` by
  `parent_branch_id` and by `parent_branch_context_id`). Before the change it aborts the same way
  the FAIL row reported, with
  `violates foreign key constraint "branch_contexts_branch_id_fkey" (SQLSTATE 23503)`.
- `TestProjectRepoDeleteProjectRemovesTaskEvents` walks the service's order on a project with a
  branch, a task and an event - `DeleteBranch` per branch, then `DeleteProject` - and counts the
  same way; at `76b0d84d` it fails at the branch step with the same 23503.

The existing branch, project and task cascade tests stay green; `go test ./...` against
`AGENTHUB_TEST_PG_URL` passes.
