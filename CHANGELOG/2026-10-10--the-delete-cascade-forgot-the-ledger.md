# The delete cascade forgot the ledger the status path had just started writing

A task that carries a single event row could not be deleted at all. The operator saw
`OPERATION_FAILED` with no reason, twice, in the same minute; reading the cause out of the code was
the only way to get one, because the error never reached the response.

## What was measured, not read

The catalogue, on the test database, lists every foreign key into `tasks`: `subtasks`,
`task_assignees`, `task_contexts`, `task_dependencies` (twice) and `task_labels` all report
`on_delete = c`, and `task_events` reports `a`. `task_event_tables.go` says why: *"No CASCADE on the
foreign key, by this schema's design: the application layer cascades."* The ledger is the one child of
a task that only this layer can remove — which makes it the one child that a manual cascade must not
forget.

`ORMTaskRepository.DeleteTask` deletes `task_contexts`, `subtasks`, `task_assignees`,
`task_dependencies` and `task_labels`, decrements the branch counters, and then deletes the task row,
all in one transaction. It had never heard of the ledger, which O1a added after it was ported. So the
parent delete was refused, the repository swallowed the refusal into `false`
(`if err != nil { return false, nil }`, Python parity), and the facade rendered that as
`Failed to delete task <id>`.

The refusal itself, captured from the swallow point rather than predicted from the shape:

```
Database operation failed: ERROR: update or delete on table "tasks" violates foreign key
constraint "task_events_task_id_fkey" on table "task_events" (SQLSTATE 23503)
```

## The fix

One statement, in the same transaction and before the task row, next to the other children:

```sql
DELETE FROM task_events WHERE task_id = $1::uuid
```

It covers subtask events too: every event row carries its parent `task_id` (NOT NULL), while
`subtask_id` is a plain `uuid` with no foreign key, so an event is addressed by its task.

`DELETE FROM tasks` appears at exactly one site in the tree, so this one statement covers every entry
point that deletes a task: the REST route, the `manage_task` MCP tool, the branch cascade, and the
repository's own `Delete` wrapper.

## A harness that manufactures the wrong finding, kept here so it is not rebuilt

A hand-seeded task cannot be used to reproduce this. The seed writes the database session's local
`now()` while the application writes UTC, and `base_timestamp_entity.go:100` refuses an entity whose
`updated_at` is earlier than its `created_at`. `GetTask` swallows that refusal through the savepoint
helper (`taskRepoOptionalStep`), so `FindByID` returns nil and the delete answers **404 Task not
found** — a plausible-looking symptom with a cause that has nothing to do with the cascade. It cost an
afternoon of hypotheses that the response could not distinguish. The regression case therefore
creates its task through the route: `POST /api/v2/tasks/` then the status change then the delete, all
three through `app.Handler()`.

## Not done, deliberately

The production row `9adab4a4` on the cloud board is left where it is: removing it would mean writing
production data to tidy up a symptom, and it rides this fix's deploy path instead. It stays the
standing reproduction until the fix is live.
