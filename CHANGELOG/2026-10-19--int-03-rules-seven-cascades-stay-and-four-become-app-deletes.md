# INT-03 rules seven cascades stay and four become application deletes

INT-03 was a GAP on a fact ("11 FK columns across 10 tables carry `ON DELETE CASCADE`") with no
decision behind it. Q7 is the decision, per column, and the register row now states it.

The schema carries 11 cascade foreign keys on 9 tables: ten in
`agenthub_go/fastmcp/task_management/infrastructure/database/models.go`
(`:762`, `:796`, `:837`, `:872`, `:906`, `:919`, `:944`, `:945`, `:953`, `:954`) and
`user_token_balances.user_id` at `models_auth.go:122`. The row's "10 tables" counted `task_events`,
whose `task_id` is the one reference into `tasks` without a cascade (`task_event_tables.go:39`); Q7
corrects the count.

Seven keep `CASCADE`, because the child belongs to exactly one aggregate and cannot outlive it, and
each parent delete either does not exist or deletes its children first:
`agent_session_events.session_id` (no code deletes an `agent_sessions` row),
`project_git_branchs.project_id` (`project_management_service.go:413` deletes the branches before
the project row at `:419`), `tasks.git_branch_id` (`git_branch_repository.go:540`), `subtasks.task_id`,
`task_assignees.task_id`, and both `task_dependencies` columns - an edge between two tasks of one
aggregate.

Four lose `CASCADE` and the application deletes the row:

| Column | The delete | Proven by |
|---|---|---|
| `task_contexts.task_id` (`models.go:919`) | `task_repository.go:677`; and a new `DELETE FROM task_contexts WHERE task_id IN (taskIDs)` before `git_branch_repository.go:540` (its steps 9-10 at `:522`/`:531` match branch ids only) | `task_repository_test.go:492` gains a `task_contexts` count; `git_branch_repository_test.go:544` gains a `task_id` count and a context with no parent ids |
| `task_labels.task_id` (`:953`) | `task_repository.go:689`; `git_branch_repository.go:504` | `git_branch_repository_test.go:544` (`:622-623` already counts by `task_id`) |
| `task_labels.label_id` (`:954`) | new `DELETE FROM task_labels WHERE label_id = $1` in `label_repository.go:225-227` - no caller exists today, so the first one would fail with 23503 | a new label-repository test: seed a link, `DeleteLabel`, count by `label_id` |
| `user_token_balances.user_id` (`models_auth.go:122`) | new `DELETE FROM user_token_balances WHERE user_id = $1` in `user_repository.go:468-470` | `auth_repositories_test.go:249` seeds a balance row and counts it after `Delete` |

The mechanism is `testdata/schema_fks.txt`: the four lines leave the golden, and
`TestSchemaInventoryPinsTenancyAndCascades` (`schema_matches_definitions_test.go:196`) fails in both
directions - a stale line and an unpinned cascade. There is no GORM in the tree; deletes are raw SQL
through `base_orm_repository.go:573`, so the child delete is a statement in the parent's delete
path, the shape `task_events` already has (`task_repository.go:703`).

No migration lands with this entry - it is the ruling and the register text. `ai_docs/` only; the
go-dev unit takes the four `OnDelete` values, the four golden lines, the three delete statements and
the four tests.

Finding, recorded not fixed: the branch and project delete paths never delete `task_events`
(`git_branch_repository.go:429-560`; reached at `project_management_service.go:413` and
`git_branch_service.go:282`), so a task with any event row blocks its branch delete with 23503 -
the defect `task_repository.go:693-703` documents for the task path.
