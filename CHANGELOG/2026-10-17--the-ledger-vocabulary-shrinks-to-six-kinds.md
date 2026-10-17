## The frontend's ledger vocabulary shrinks to the six kinds the server keeps

The hub's ledger deleted six task-event kinds (`48c96fdd`, `task_event.go`): `assigned`, `claimed`,
`delivered`, `context_loaded`, `escalated`, `human_decision`. Each was removed because nothing writes
it and every one of its facts already has a single home - assignment is the task's assignees column, a
claim is the `status_changed` write, a delivery is a queue row, an escalation is a
`task_audit_records` row, an owner decision is a queue row. The frontend still mirrored the old
twelve, so its type claimed kinds the server's CHECK constraint refuses.

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

### Ordering
- This narrows the client to the vocabulary `48c96fdd` lands on the hub. If it is integrated BEFORE
  that commit, the client lists fewer kinds than the hub's CHECK still accepts - no kind it drops has
  a writer, so nothing renders differently, but the two files mirror each other only once both land.
