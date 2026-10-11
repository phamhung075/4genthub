// The execution ledger's DERIVED phase, and the labels its rows and badge use.
//
// THE PHASE IS COMPUTED FROM THE EVENTS AND NEVER STORED AS A SECOND STATUS - the architecture's
// own words (`ai_docs/core-architecture/agenthub-system-architecture.md:173`, `:389`). That is why
// everything here is a pure function of the event sequence: nothing reads the task row's `status`,
// so a task whose stored status and ledger disagree cannot make the timeline claim the stored one.
//
// THE PHASE MOVES ON `status_changed` AND ON NOTHING ELSE, and that is the VOCABULARY's shape rather
// than this file's limit: of the twelve kinds the ledger's CHECK constraint enforces
// (`ck_task_event_kind`, `.../infrastructure/database/task_event_tables.go:40`, mirrored by
// `TaskEventKindValues` in `domain/entities/task_event.go:56-68`), only `status_changed` carries a
// status - `{ old, new }`, the pair the server's own parity check reads against `tasks.status`. The
// other eleven say that something HAPPENED - a claim, a delivery, a verdict - not which phase the task
// is in, so folding a phase out of one would read a meaning out of a payload shape nothing defines.
//
// WHAT THE LEDGER CANNOT YET SAY, THE UI SAYS: `evidence_submitted` and `gate_verdict` ARE in the
// vocabulary, but no writer emits them yet - `status_changed` is still the only emitted kind
// (`RecordStatusChange`, `application/services/task_event_recorder.go:74`). `LEDGER_NOT_RECORDED`
// below is what the timeline shows instead of letting a status move read as a passing test.

import type { TaskEvent, TaskEventActorKind, TaskEventKind, TaskStatus } from '../types/taskTypes';

/** The phases a viewer can see, all derived. `unopened` is not `todo`: an empty ledger is silent. */
export type LedgerPhase = 'unopened' | TaskStatus;

const STATUSES: readonly string[] = [
  'todo',
  'in_progress',
  'blocked',
  'review',
  'testing',
  'done',
  'cancelled',
];

/**
 * The nearest thing the ledger can show for the steps it cannot yet distinguish. Rendered as a muted
 * note under the timeline, because a status change to `testing` or `review` is NOT evidence that a
 * test passed, and the timeline must not read as if it were.
 */
export const LEDGER_NOT_RECORDED =
  'The ledger has a gate-verdict kind and an evidence kind, but no writer emits them yet, so a step ' +
  'here means the task moved - not that its tests passed.';

/** Human labels for the phase badge. Kept beside the phase type so the two cannot drift apart. */
export const PHASE_LABELS: Record<LedgerPhase, string> = {
  unopened: 'No events',
  todo: 'Todo',
  in_progress: 'In progress',
  blocked: 'Blocked',
  review: 'Review',
  testing: 'Testing',
  done: 'Done',
  cancelled: 'Cancelled',
};

/**
 * ONE LABEL PER KIND, EXHAUSTIVE BY TYPE - `Record<TaskEventKind, string>` is what turns a new member of
 * `TASK_EVENT_KINDS` into a compile error here rather than a raw identifier on screen, and
 * `src/tests/lib/taskTimeline.test.ts` asserts the same invariant at run time (every kind has a label
 * that is neither empty nor the kind itself). `status_changed` has a label like the rest: it is the
 * fallback `describeEvent` uses for a row whose payload defines no transition.
 */
export const KIND_LABELS: Record<TaskEventKind, string> = {
  assigned: 'Assigned',
  claimed: 'Claimed',
  delivered: 'Delivered',
  context_loaded: 'Context loaded',
  progress: 'Progress reported',
  status_changed: 'Status changed',
  evidence_submitted: 'Evidence submitted',
  gate_verdict: 'Gate verdict',
  escalated: 'Escalated',
  human_decision: 'Human decision',
  handover: 'Handover',
  context_updated: 'Context updated',
};

/**
 * ONE LABEL PER ACTOR CLASS, exhaustive by type for the same reason: the four are the ledger's
 * `ck_task_event_actor_kind` (`task_event_tables.go:40`). The three this map used to carry
 * (`user | system | agent`) are gone from the server, and `system` is gone ON PURPOSE - an
 * unattributable write is refused rather than stamped with a class nothing acted as
 * (`domain/entities/task_event.go:71-86`).
 */
export const ACTOR_LABELS: Record<TaskEventActorKind, string> = {
  seat: 'a seat',
  client: 'a client',
  gate: 'a gate',
  human: 'a person',
};

/**
 * Reads `status_changed`'s `{ old, new }` payload. An unreadable payload returns null and the caller
 * keeps the phase it had: a malformed payload must not invent a status.
 */
export function statusChangedTo(event: TaskEvent): TaskStatus | null {
  // The doc above says `status_changed`, so the KIND is checked rather than assumed: a `progress`
  // payload that happens to carry a `new` is not a status change, and the fold's own rule is that no
  // kind may be read for a meaning its payload shape does not define.
  if (event.kind !== 'status_changed') return null;
  const next = event.payload?.['new'];
  return typeof next === 'string' && STATUSES.includes(next) ? (next as TaskStatus) : null;
}

/**
 * The phase the sequence ends in, read oldest-first (`seq` ascending, which is the order the route
 * returns). One rule, tied to the kind that carries a status:
 * - `status_changed` carries the status the task reached, so it sets the phase.
 * - EVERY OTHER KIND DELIBERATELY DOES NOT MOVE IT - a claim, a delivery, a progress note, a verdict.
 *   `unopened` is an empty ledger: silence, not `todo`.
 */
export function deriveLedgerPhase(events: readonly TaskEvent[]): LedgerPhase {
  let phase: LedgerPhase = 'unopened';
  for (const event of events) {
    if (event.kind === 'status_changed') {
      phase = statusChangedTo(event) ?? phase;
    }
  }
  return phase;
}

/** One row's headline. Names the transition when the payload defines one, the kind's label otherwise. */
export function describeEvent(event: TaskEvent): string {
  if (event.kind === 'status_changed') {
    const from = event.payload?.['old'];
    // READ THE RECORD, NOT THE VOCABULARY: the phase fold must reject a status it does not know, but a
    // ROW must not - a backend that grows a status should show it here on the day it does, and a row
    // that said only "Status changed" would be hiding what the ledger actually wrote.
    const to = event.payload?.['new'];
    if (typeof to === 'string' && typeof from === 'string') return `Status: ${labelOf(from)} to ${labelOf(to)}`;
    if (typeof to === 'string') return `Status: ${labelOf(to)}`;
  }
  return labelForKind(event.kind);
}

/**
 * A kind's display name for a value off the WIRE, which may be one this build does not know: the twelve
 * are the whole vocabulary today, and a kind the server adds tomorrow is still what happened, so it
 * prints as itself rather than as nothing.
 */
export function labelForKind(kind: string): string {
  return (KIND_LABELS as Record<string, string>)[kind] ?? kind;
}

/**
 * A status's display name, taken from `PHASE_LABELS` so a status has ONE name in this UI rather
 * than a second map here. An unknown status prints as itself - the ledger is the record, and a
 * value this build does not know is still what happened.
 */
function labelOf(status: string): string {
  return (PHASE_LABELS as Record<string, string>)[status] ?? status;
}
