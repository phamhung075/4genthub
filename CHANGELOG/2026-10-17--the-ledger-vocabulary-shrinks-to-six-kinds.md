## The frontend's ledger vocabulary shrinks to the six kinds that have writers

`a373feec` (landed on main) deletes six task-event kinds from the hub's ledger: `assigned`, `claimed`,
`delivered`, `context_loaded`, `escalated`, `human_decision`, and gives `handover` its one writer. The
frontend mirrored the old twelve, so its type claimed kinds the ledger can no longer record. The hub's
four declarations now name the same six this array does, in the same order: the constants and
`TaskEventKindValues` in `domain/entities/task_event.go`, `ck_task_event_kind` in
`task_event_tables.go`, the ensurer's `taskEventKindVocabulary`, and the baseline migration. Each of
the six has a writer - `status_changed` RecordStatusChange, `progress` RecordProgress, `gate_verdict`
RecordGateVerdict, `evidence_submitted` the evidence route and the sweeper, `context_updated`
update_context and the unified context service, `handover` the ledger outbox's payload gate, which
resume then reads. Every fact the dropped kinds named already has a single home: assignment is the
task's assignees column, a claim is the `status_changed` write, a delivery is a queue row, an
escalation is a `task_audit_records` row, an owner decision is a queue row, and no hub path loads
context.

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
- The two sides landed in either order without harm, which was checked rather than assumed: with the
  hub still declaring twelve, `grep -rn "TaskEventKind<Kind>\b" --include='*.go' agenthub_go`
  (excluding `_test.go` files and the vocabulary definition in `domain/entities/task_event.go` and
  `task_event_ensurer.go`) returned 0 for each of the six dropped kinds and at least 1 for each of the
  six kept ones, so the client could not hide a row a writer could still produce.
- The frontend commits are `21866770` (the narrowing), `c6f88c1c` (the measured emitters, replacing a
  handover writer that did not exist yet) and the follow-up that matches the comments to `a373feec`.
  No `agenthub_go/` file is touched by any of them.
