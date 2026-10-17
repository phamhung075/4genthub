# `manage_task get` returns the completion summary it stored

Board task `5420da8e`: `manage_task complete` accepts a `completion_summary`, the repository stores it
(`tasks.completion_summary`) and reads it back onto the entity, and then `TaskResponse` — the only
DTO both the MCP `get` path and `GET /api/v2/tasks/{id}` serialize — had no field for it. `ToDict`
dropped it. So a closure whose only record was the summary could not be read back by anyone,
including the next lead after a compaction: the board is this pod's system of record.

I hit this myself minutes before picking the row up: completing `0a30dd7e` and then reading the task
back showed every other field and no completion line at all.

## Fixed

- `application/dtos/task/task_response.go`: `TaskResponse` gained `CompletionSummary` and
  `TestingNotes`; `TaskResponseFromDomain` copies both from the entity's dict (the entity already
  emitted them — `entities/task.go:1133`), and `ToDict` emits `completion_summary` and
  `testing_notes` after `details`.

Both read surfaces are fixed by that one change, because both consume this DTO:
`TaskApplicationFacade.GetTask` (MCP `manage_task get`) and `routes.GetUserTask`
(`GET /api/v2/tasks/{id}`).

An un-completed task answers no key rather than an empty one: `ResponseOptimizer.RemoveNulls` drops
empty strings by design, and "no summary" is expressed by absence, never by a value that could be
mistaken for a stored one. The test pins that too.

## Tests

- `TestMCPCompleteSummaryIsReadableFromGet` (`fastmcp/server/httpapp`, real Postgres, real
  `POST /mcp`): creates a task through `tools/call manage_task {action:create}`, completes it with a
  distinctive 54-character summary, then reads it back through `action:get` and requires the text
  verbatim; then clears the column and requires the key to be ABSENT rather than empty. Red before
  the fix at the `completion_summary` key and nowhere else.
- The two pinned key lists that describe this response (`TestTaskResponseToDict`,
  `createTaskResponseKeys` shared by the create and update use-case tests) gained the two keys — the
  shape change is the fix, so the lists follow it.

## Verification

- `go build ./...`, `gofmt -l` on the touched trees, `go vet` on the touched packages: clean.
- `go test ./fastmcp/task_management/application/... ./fastmcp/task_management/interface/...`: pass.
- `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55461/postgres go test
  ./fastmcp/server/httpapp/`: pass.
