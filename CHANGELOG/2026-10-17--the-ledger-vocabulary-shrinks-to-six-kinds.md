## The frontend's ledger vocabulary shrinks to the six kinds that have writers

`48c96fdd` (go-dev, not yet in main) deletes six task-event kinds from the hub's ledger:
`assigned`, `claimed`, `delivered`, `context_loaded`, `escalated`, `human_decision`. The frontend
mirrored the old twelve, so its type claimed kinds the ledger can no longer record. The narrowing does
not depend on that commit landing first: counted on main on 2026-10-17, every one of the six dropped
kinds has zero non-test references in `agenthub_go` outside the vocabulary definition itself, and each
of the six kept kinds has a writer (`status_changed` RecordStatusChange, `progress` RecordProgress,
`gate_verdict` RecordGateVerdict, `evidence_submitted` the evidence route and the sweeper,
`context_updated` update_context and the unified context service) - except `handover`, which resume
reads and whose writer is queued on `bb5e5022`. So the client cannot drop a row that a writer could
still produce, in either integration order. Every fact the dropped kinds named already has a single
home: assignment is the task's assignees column, a claim is the `status_changed` write, a delivery is a
queue row, an escalation is a `task_audit_records` row, an owner decision is a queue row.

### Changed
- `agenthub-frontend/src/types/taskTypes.ts`: `TASK_EVENT_KINDS` is the six that remain - `progress`,
  `status_changed`, `evidence_submitted`, `gate_verdict`, `handover`, `context_updated` - and the
  comment states the rule that survives the narrowing: `status_changed` is the only kind whose payload
  defines a status (`{ old, new }`), so a `new` on any other kind is unknown, not a phase.
- `agenthub-frontend/src/lib/taskTimeline.ts`: `KIND_LABELS` drops the six dead labels (the map is
  `Record<TaskEventKind, string>`, so it cannot keep one). `LEDGER_NOT_RECORDED` said the verdict kinds
  had no writer, which the six-kind set contradicts - `gate_verdict` and `evidence_submitted` have
  their own writers - and now says what is still true: a step means the task moved, and a pass is a
  verdict or evidence row of its own. The phase fold is unchanged: `status_changed` and nothing else.

### Testing
- `agenthub-frontend/src/tests/lib/taskTimeline.test.ts`: the phase-fold case now puts every surviving
  non-status kind around the one `status_changed` (including `evidence_submitted` carrying a `new` on
  purpose), and the label case names four of them instead of two deleted ones. The exhaustive
  `it.each(TASK_EVENT_KINDS)` label invariant follows the array, so a kind added without a label still
  fails.
- RUN: `npx tsc --noEmit -p .` exits 0; `npx vitest run src/tests/lib/taskTimeline.test.ts` = 1 file /
  20 tests, 0 failed.

### Ordering and evidence
- No integration order is required. The rule the narrowing rests on was measured rather than inferred
  from `48c96fdd`: `grep -rn "TaskEventKind<Kind>\b" --include='*.go' agenthub_go`, excluding `_test.go`
  files and the vocabulary definition in `domain/entities/task_event.go` and
  `task_event_ensurer.go`, returns 0 for each of the six dropped kinds and at least 1 for each of the
  six kept ones. A comment in `task_event.go` claims every kind in its list has a writer; this count is
  the counter-evidence for six of them (handover's writer is still queued), and it is why the client's
  narrower set cannot hide a row.
- Deliberately not done here: the hub's own file and its migration. `48c96fdd` carries those, and a
  frontend commit does not edit `agenthub_go/`.
