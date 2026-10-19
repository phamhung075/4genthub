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
  before step 13 deletes the tasks. Later steps are renumbered 11-15.
- **The aggregate-scope rule (ruling `RULING-int03-branch-delete-scope-2026-10-20.md`, option B).**
  `DeleteBranch` is aggregate-scoped, not author-scoped: the project-ownership check at the top of
  the method is the one tenancy boundary, and the body then runs with NO `user_id` condition at all -
  all eleven `gitBranchRepoUserCond` sites are gone (and the helper with them: this was its last
  caller), and both id selects pass `userScoped=false`. A child's `user_id` is its author, and it can
  never be a control here: where the schema cascades (`tasks`, `subtasks`, `task_assignees`,
  `task_dependencies`) the filter deletes a subset the database would take anyway; where it does not
  (`task_contexts`, `task_labels`, `branch_contexts`, `task_events`) it leaves another author's row
  behind and the branch row refuses to go with 23503. The deleted worktree of a branch is its
  aggregate: the branch is the unit, and the gate is the only question of tenancy in the path.
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
