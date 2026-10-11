import React from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Badge } from './ui/badge';
import { useTaskEvents } from '../hooks/useTasks';
import {
  ACTOR_LABELS,
  LEDGER_NOT_RECORDED,
  PHASE_LABELS,
  deriveLedgerPhase,
  describeEvent,
} from '../lib/taskTimeline';
import { getStatusEmoji } from '../utils/statusEmojis';
import { cleanProgressText, parseProgressHistory } from '../utils/progressHistoryUtils';
import type { ProgressEntry } from '../types/utilityTypes';
import type { TaskEvent } from '../types/taskTypes';

export interface TaskEventTimelineProps {
  /**
   * The task whose ledger to render.
   *
   * THERE IS DELIBERATELY NO STATUS PROP: the phase is derived from the events and never read from
   * the task, and taking only an id is what makes that true by construction rather than by promise.
   */
  taskId: string | undefined;
  /**
   * The served merged progress text (the task's `details`): the `progress_history` column's notes
   * joined with the ledger's, one section per note in progress order. It supplies ROWS ONLY - the
   * phase above the list is still a function of the events alone - and it is here because the ledger
   * ALONE has no row for a note written before the dual-write switch.
   */
  progressHistory?: string;
  className?: string;
}

/**
 * The one phase that is NOT a task status, so it has no entry in the status emoji map. The badge reads
 * `LEDGER_PHASE_EMOJI[phase] ?? getStatusEmoji(phase)`, so every other phase is a status and takes its
 * emoji from there. The actor labels live with the rest of the ledger vocabulary in `lib/taskTimeline`,
 * where a missing one is a compile error rather than a raw class string on screen.
 */
const LEDGER_PHASE_EMOJI: Record<string, string> = {
  unopened: '⚪',
};

const formatWhen = (iso: string): string => {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? iso : at.toLocaleString();
};

/**
 * A `progress` event's note, cleaned the way its row renders it, so the merge below compares the two
 * sources on the same text. Every other kind - and a progress event with no usable `content` - yields
 * the empty string, which the caller drops.
 */
const ledgerNote = (event: TaskEvent): string => {
  if (event.kind !== 'progress') return '';
  const content = event.payload?.['content'];
  return typeof content === 'string' ? cleanProgressText(content) : '';
};

/**
 * A `progress` event's own progress number, when its payload carries one - the ledger's writer emits
 * `{ content, progress_number }`. It is the scale the merged text numbers its notes on, so it is what
 * lets a note with no event be PLACED against the ledger's notes instead of appended after them.
 */
const ledgerProgressNumber = (event: TaskEvent): number | null => {
  if (event.kind !== 'progress') return null;
  const value = event.payload?.['progress_number'];
  return typeof value === 'number' ? value : null;
};

/**
 * The task's EXECUTION LEDGER (`task_events`) as a timeline, plus the notes only the served merged
 * text (`progressHistory`) has.
 *
 * The badge above the list is `deriveLedgerPhase(events)` - a fold over the sequence, not a field -
 * so a task whose stored status and ledger disagree shows the LEDGER's phase. What the vocabulary
 * cannot express is stated under the list rather than dressed up: a status change to `testing` or
 * `review` is not evidence that a test passed (see `LEDGER_NOT_RECORDED`).
 *
 * A progress note IS the thing its event exists to carry, so the note's own text is the row. But a
 * note written before the dual-write switch has no event at all, and the served `progressHistory`
 * joins the column's notes with the ledger's for exactly that reason: the survivors - the column
 * entries no fetched `progress` event already shows - become rows of the SAME list, placed on the
 * ledger's own progress numbers rather than appended after it, so a pre-switch note reaches the
 * reader again AND in its own place, and the timeline stays the one progress surface.
 */
export const TaskEventTimeline: React.FC<TaskEventTimelineProps> = ({ taskId, progressHistory, className = '' }) => {
  const { data, isLoading, error } = useTaskEvents(taskId);
  const events: TaskEvent[] = data?.events ?? [];

  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 text-sm text-muted-foreground ${className}`}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Loading execution ledger…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center gap-2 text-sm text-muted-foreground ${className}`}>
        <AlertCircle className="w-4 h-4" />
        <span>Execution ledger unavailable.</span>
      </div>
    );
  }

  const phase = deriveLedgerPhase(events);

  // WHICH NOTES THE LEDGER CANNOT SHOW. The producer joins the two sources on `(progress_number,
  // content)` and renders each note once, so a column entry the ledger ALSO carries must not become a
  // second row. The key is the pair whenever the event's own number is known, and the text alone when
  // it is not: keying on text alone would drop a genuinely distinct note that repeats another's
  // wording, and keying on the pair alone would duplicate every note whose event predates
  // `progress_number` reaching the wire.
  const ledgerKeys = new Set<string>();
  for (const event of events) {
    const note = ledgerNote(event);
    if (note === '') continue;
    const number = ledgerProgressNumber(event);
    ledgerKeys.add(number === null ? note : `${number}|${note}`);
  }
  const historyOnly = parseProgressHistory(progressHistory).filter(entry => {
    const note = cleanProgressText(entry.content);
    return !ledgerKeys.has(note) && !ledgerKeys.has(`${entry.number}|${note}`);
  });

  // ORDER. `parseProgressHistory` sorts by number and a ledger `progress` row carries the same number,
  // so a surviving note is placed on that shared scale: it goes before the first ledger note numbered
  // past it, and after the last one when nothing is. Rows of other kinds - status changes and the like
  // - keep their `seq` positions and are never displaced by a note, which has no seq to be measured
  // against.
  const ordered: Array<{ kind: 'event'; event: TaskEvent } | { kind: 'history'; entry: ProgressEntry }> = [];
  const pending = [...historyOnly];
  for (const event of events) {
    const number = ledgerProgressNumber(event);
    if (number !== null) {
      let placed = 0;
      while (placed < pending.length && pending[placed].number < number) {
        ordered.push({ kind: 'history', entry: pending[placed] });
        placed += 1;
      }
      if (placed > 0) pending.splice(0, placed);
    }
    ordered.push({ kind: 'event', event });
  }
  for (const entry of pending) ordered.push({ kind: 'history', entry });

  const hasRows = events.length > 0 || historyOnly.length > 0;

  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-medium">Execution Ledger</span>
        <Badge variant="secondary" className="text-xs" aria-label={`Ledger phase: ${PHASE_LABELS[phase]}`}>
          {LEDGER_PHASE_EMOJI[phase] ?? getStatusEmoji(phase)} {PHASE_LABELS[phase]}
        </Badge>
        <Badge variant="outline" className="text-xs">
          {events.length}
        </Badge>
      </div>

      {!hasRows ? (
        <p className="text-xs text-muted-foreground">
          No ledger events for this task yet.
        </p>
      ) : (
        <>
          <ol className="space-y-2">
            {ordered.map(row => row.kind === 'event' ? (
              <li key={row.event.id} className="flex items-start gap-2 text-sm">
                <Badge variant="outline" className="text-xs shrink-0 font-mono">
                  {row.event.seq}
                </Badge>
                <div className="min-w-0">
                  <div className="font-medium">{describeEvent(row.event)}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatWhen(row.event.created_at)} · {ACTOR_LABELS[row.event.actor_kind] ?? row.event.actor_kind}
                    {row.event.actor_id ? ` (${row.event.actor_id})` : ''}
                  </div>
                </div>
              </li>
            ) : (
              <li key={`history-${row.entry.number}`} className="flex items-start gap-2 text-sm">
                <Badge variant="outline" className="text-xs shrink-0 font-mono">
                  {row.entry.number}
                </Badge>
                <div className="min-w-0">
                  <div className="font-medium">{cleanProgressText(row.entry.content)}</div>
                  <div className="text-xs text-muted-foreground">
                    From the task's progress history
                  </div>
                </div>
              </li>
            ))}
          </ol>
          {events.length > 0 && <p className="text-xs text-muted-foreground mt-3">{LEDGER_NOT_RECORDED}</p>}
        </>
      )}
    </div>
  );
};
