# A done task keeps its result line, its author and its time

Board task `ca541a97`: `manage_task complete` on a task that is ALREADY done rewrote its
`completion_summary` - the ledger's result line, another seat's evidence - answered success, and left
no record of who wrote the new sentence or when. The write was defensible (correcting a bad line is
reasonable); the silence was not.

## What changed

- **Attribution is on the row.** `tasks.completed_by` records the seat (`<room>/<seat>`) that wrote
  the result line, falling back to the user id on a request that named no seat, and
  `tasks.completed_at` - a column the table always had and nothing ever wrote - records when. Both are
  returned by `manage_task get` and `GET /api/v2/tasks/{id}` as `completed_by` and `completed_at`.
  The column reaches an existing database through `EnsureTaskCompletedByColumn` (registered in
  `ColumnEnsurers`, `AUTO_MIGRATE=true`), the baseline migration and the embedded init schema.
- **The already-done branch is a gate, not a rewrite.** A complete that carries no summary, or the
  summary the row already holds, writes NOTHING - the old code saved and moved `updated_at` anyway,
  which told every reader the task had changed. A different summary is refused unless the caller is
  the author of record or passes `correction=true`; the refusal names the author and the way forward.
- **A replaced line stays legible.** The replacement writes one `progress` ledger entry, in the same
  transaction as the row save, carrying the previous text, its author and its time, attributed to the
  seat that made the replacement - readable at `GET /api/v2/tasks/{id}/events`.
- **`correction` is a declared MCP parameter** (`manage_task`, boolean, default false), in the tool
  schema and its golden. Every other entry point completes without it.

## Verification

- `go test ./fastmcp/task_management/...` pass; `go build ./...` clean.
- `AGENTHUB_TEST_PG_URL=... go test ./fastmcp/task_management/infrastructure/database/
  ./fastmcp/task_management/infrastructure/repositories/` pass (the ensurer and the TableDef/baseline
  parity guard among them).
- `AGENTHUB_TEST_PG_URL=... go test ./fastmcp/server/httpapp/ -run
  'TestMCPCompleteOnADoneTaskIsAttributedAndGated'` passes: first completion records seat `go-dev`;
  a second seat without the flag is refused and the line is untouched; with the flag the line is
  replaced and `completed_by` moves to the replacing seat; the superseded entry names the old line,
  its author and the replacer; repeating the same completion adds no entry.

## Known, unrelated

`./fastmcp/server/httpapp/` still fails
`TestLedgerIntentsOneBatchDecidesEachItemAndAnswersTheResendFromItsRow` and
`TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder` on `unsupported_kind` - the ledger
intents vocabulary, untouched by this change and by the previous completion-summary fix.
