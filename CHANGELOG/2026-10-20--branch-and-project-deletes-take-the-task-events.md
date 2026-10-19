# INT-03 residual: the branch and project deletes take the task-event ledger with them

`task_events.task_id` is the one foreign key into `tasks` with no `ON DELETE CASCADE`
(`task_event_tables.go`: the application layer cascades by design). The task delete already
deletes its ledger (`task_repository.go`), but two other paths removed tasks without it, so each
aborted with SQLSTATE 23503 whenever a task had an event row:

- `ORMGitBranchRepository.DeleteBranch` (`git_branch_repository.go`): the per-task group (steps
  5-9) now ends with step 10, `task_events` by the branch's task ids, before step 13 deletes the
  tasks. Later steps are renumbered 11-15; no statement changed other than the new one.
- `ORMProjectRepository.DeleteProject` (`project_repository.go`): the delete now runs in one
  transaction and removes the ledger of every task under the project's branches first - the
  branches and tasks themselves still leave through the schema's two cascades.

Tests (both red at `76b0d84d` with
`ERROR: update or delete on table "tasks" violates foreign key constraint "task_events_task_id_fkey" (SQLSTATE 23503)`,
green after the change):

- `TestGitBranchRepoDeleteBranchRemovesTaskEvents` seeds a branch task and one event through
  `TaskEventRepository.Append`, deletes the branch, and counts `task_events` by `task_id`.
- `TestProjectRepoDeleteProjectRemovesTaskEvents` seeds a project with a branch, a task and an
  event, deletes the project, and counts the same way.

The existing branch, project and task cascade tests stay green; `go test ./...` against
`AGENTHUB_TEST_PG_URL` passes.
