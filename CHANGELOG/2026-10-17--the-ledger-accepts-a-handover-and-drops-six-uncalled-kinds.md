# The ledger accepts a handover, and the event vocabulary narrows to six kinds

## Added

- `fastmcp/ledger/domain/entities/handover.go`: `ValidateHandoverPayload`, the 1/8 ruling's payload checked at
  the ledger's one write gate. The key set is closed (`facts`, `rule`, `decision`, `next`, plus the ruled
  per-decision keys): exactly these, an unknown or missing key is refused. `decision` is
  `continue|blocked|done|escalate`; `next_action` is required for `continue|blocked|escalate`, capped at 200
  chars and single-line; `blocked_on` is required for `blocked|escalate` and refused otherwise; `facts` is 1..8
  items of `{claim, evidence}`, the claim capped at 160 chars and the evidence matching one of the four ref
  grammars (`sha:<8 hex>`, `evt:<uuid>`, `qitem:<id>`, `task:<uuid>`); `constraints` is at most 8 refs; the
  payload as serialized is capped at 2048 bytes. Refusal tokens: `handover_malformed` and
  `handover_fact_without_evidence`. An `evt:` ref is resolved inside the caller's task, so citing another
  task's entry is refused; a resolver failure is an ERROR, never a refusal.
- `fastmcp/ledger/application/services/ledger_service.go`: the payload check sits beside `IsIntentKind`, after
  the task identity is resolved, so the outbox and any future writer pass one gate.
- `fastmcp/task_management/infrastructure/repositories/task_event_repository.go`: `EventInTask`, one query over
  the same table the handover is appended to, scoped by user as well as task.

## Changed

- The kind vocabulary is six kinds - `progress`, `status_changed`, `evidence_submitted`, `gate_verdict`,
  `handover`, `context_updated` - in all four places that declare it: `TaskEventKindValues`
  (`task_management/domain/entities/task_event.go`), the hardcoded vocabulary in
  `task_event_ensurer.go`, `task_event_tables.go`, and `migrations/0001_baseline.sql`. The ensurer counts rows
  carrying one of the six deleted kinds BEFORE it re-adds the CHECK, so an operator gets a count to migrate
  instead of the driver's opaque constraint failure at every start; the baseline migration and the runtime DDL
  now match byte for byte (the schema-matches-definitions test pinned the drift).
- `fastmcp/ledger/domain/entities/intent.go`: five intent kinds (`progress`, `status_changed`,
  `evidence_submitted`, `gate_verdict`, `handover`); the comment that claimed `delivered` and `escalated` were
  server-written is corrected - neither had a writer, a handoff is a queue row and an escalation is a
  `task_audit_records` row - and `context_updated` stays the server's own, non-intent kind.

## Removed

- `assigned`, `claimed`, `delivered`, `context_loaded`, `escalated`, `human_decision`. Their facts have a single
  home: assignment is the task's assignees column, a claim is the `status_changed` write, a delivery is a queue
  row, an escalation is a `task_audit_records` row, and an owner decision is a queue row.

## Verified

- `cd agenthub_go && go test -count=1 ./...` exits 0: 140 packages ok, 0 failures.
- `ledger_pg_test.go` runs the production seam (session manager, real route): one accepted handover is read back
  by `GET /api/v2/tasks/{id}/resume` as `last_handover` verbatim, and the batch's four refusals - missing key,
  unknown key, fact without evidence, and an `evt:` of another task - each answer the ruled token while the row
  count grows by exactly one.
- `handover_test.go`: one accepted payload per decision value, 24 malformed cases, 12 evidence cases (including
  a false-resolving `evt:`), the resolver-failure propagation, and the serialized byte cap.
- `task_event_ensurer_test.go`: a legacy row carrying a deleted kind is reported by count before the CHECK is
  re-added.
