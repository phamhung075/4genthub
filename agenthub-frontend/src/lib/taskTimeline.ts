// The execution ledger's DERIVED phase.
//
// THE PHASE IS COMPUTED FROM THE EVENTS AND NEVER STORED AS A SECOND STATUS - the architecture's
// own words (`ai_docs/core-architecture/agenthub-system-architecture.md:173`, `:389`). That is why
// everything here is a pure function of the event sequence: nothing reads the task row's `status`,
// so a task whose stored status and ledger disagree cannot make the timeline claim the stored one.
//
// THE VOCABULARY IS SMALLER THAN THE DESIGN SAYS, AND THIS FILE SAYS SO RATHER THAN IMPLYING MORE:
// the ledger's CHECK constraint carries `created | updated | status_changed | completed | deleted`
// and `status_changed` is the ONLY kind any writer emits today, with the only defined payload shape
// `{ old, new }`. The richer steps on the architecture's worked example - `evidence_submitted` for a
// test outcome, `gate_verdict` for ACCEPT/REJECT - are NOT IN THE VOCABULARY AND NOT BUILT (they are
// O3's and O5's). So no function here invents them, and `LEDGER_NOT_RECORDED` below is what the UI
// shows instead of pretending a status change means the tests passed.

import type { TaskEvent, TaskEventKind, TaskStatus } from '../types/taskTypes';

/** The phases a viewer can see, all derived. `unopened` is not `todo`: an empty ledger is silent. */
export type LedgerPhase =
  | 'unopened'
  | 'created'
  | 'completed'
  | 'deleted'
  | TaskStatus;

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
 * The nearest thing the ledger can show for the steps it cannot distinguish. Rendered as a muted
 * note under the timeline, because a status change to `testing` or `review` is NOT evidence that a
 * test passed, and the timeline must not read as if it were.
 */
export const LEDGER_NOT_RECORDED =
  'The ledger records status changes only. Test outcomes and gate verdicts are not in the event ' +
  'vocabulary yet, so a step here means the task moved - not that its tests passed.';

/** Human labels for the phase badge. Kept beside the phase type so the two cannot drift apart. */
export const PHASE_LABELS: Record<LedgerPhase, string> = {
  unopened: 'No events',
  created: 'Created',
  todo: 'Todo',
  in_progress: 'In progress',
  blocked: 'Blocked',
  review: 'Review',
  testing: 'Testing',
  done: 'Done',
  completed: 'Completed',
  cancelled: 'Cancelled',
  deleted: 'Deleted',
};

/**
 * Reads `status_changed`'s `{ old, new }` payload. An unreadable payload returns null and the
 * caller keeps the phase it had: a malformed payload must not invent a status.
 */
export function statusChangedTo(event: TaskEvent): TaskStatus | null {
  // The doc above says `status_changed`, so the KIND is checked and not merely assumed: an
  // `updated` payload that happens to carry a `new` is not a status change, and the fold's own rule
  // is that a kind nothing defines must not be read as one.
  if (event.kind !== 'status_changed') return null;
  const next = event.payload?.['new'];
  return typeof next === 'string' && STATUSES.includes(next) ? (next as TaskStatus) : null;
}

/**
 * The phase the sequence ends in, read oldest-first (`seq` ascending, which is the order the route
 * returns). Rules, each tied to the kind it comes from:
 * - `created` says the ledger opened; `completed` and `deleted` are terminal and say so directly.
 * - `status_changed` carries the status the task reached, so it sets the phase.
 * - `updated` says something changed, not WHICH phase it is, so it deliberately does not move the
 *   phase - moving it would mean reading a meaning out of a payload shape nothing defines.
 */
export function deriveLedgerPhase(events: readonly TaskEvent[]): LedgerPhase {
  let phase: LedgerPhase = 'unopened';
  for (const event of events) {
    switch (event.kind) {
      case 'created':
        phase = 'created';
        break;
      case 'completed':
        phase = 'completed';
        break;
      case 'deleted':
        phase = 'deleted';
        break;
      case 'status_changed':
        phase = statusChangedTo(event) ?? phase;
        break;
      case 'updated':
        break;
    }
  }
  return phase;
}

/** One row's headline. Names the transition when the payload defines one, the kind otherwise. */
export function describeEvent(event: TaskEvent): string {
  if (event.kind === 'status_changed') {
    const from = event.payload?.['old'];
    // READ THE RECORD, NOT THE VOCABULARY: the phase fold must reject a status it does not know,
    // but a ROW must not - a backend that grows a status should show it here on the day it does,
    // and a row that said only "Status changed" would be hiding what the ledger actually wrote.
    const to = event.payload?.['new'];
    if (typeof to === 'string' && typeof from === 'string') return `Status: ${labelOf(from)} to ${labelOf(to)}`;
    if (typeof to === 'string') return `Status: ${labelOf(to)}`;
    return 'Status changed';
  }
  switch (event.kind as TaskEventKind) {
    case 'created':
      return 'Created';
    case 'completed':
      return 'Completed';
    case 'deleted':
      return 'Deleted';
    case 'updated':
      return 'Updated';
    default:
      return String(event.kind);
  }
}

/**
 * A status's display name, taken from `PHASE_LABELS` so a status has ONE name in this UI rather
 * than a second map here. An unknown status prints as itself - the ledger is the record, and a
 * value this build does not know is still what happened.
 */
function labelOf(status: string): string {
  return (PHASE_LABELS as Record<string, string>)[status] ?? status;
}
