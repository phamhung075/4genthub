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
 * entries no fetched `progress` event already shows - are appended as rows of the SAME list, so the
 * timeline stays the one progress surface while a pre-switch note reaches the reader again.
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

  // The notes the ledger cannot show, in the merged text's own progress order (parseProgressHistory
  // sorts by number). A column entry the ledger also has is DROPPED: the served text renders each note
  // once, and a note must not appear twice on screen because both sources carry it.
  const ledgerNotes = new Set(events.map(ledgerNote).filter(note => note !== ''));
  const historyOnly = parseProgressHistory(progressHistory).filter(
    entry => !ledgerNotes.has(cleanProgressText(entry.content)),
  );

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
            {events.map(event => (
              <li key={event.id} className="flex items-start gap-2 text-sm">
                <Badge variant="outline" className="text-xs shrink-0 font-mono">
                  {event.seq}
                </Badge>
                <div className="min-w-0">
                  <div className="font-medium">{describeEvent(event)}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatWhen(event.created_at)} · {ACTOR_LABELS[event.actor_kind] ?? event.actor_kind}
                    {event.actor_id ? ` (${event.actor_id})` : ''}
                  </div>
                </div>
              </li>
            ))}
            {historyOnly.map(entry => (
              <li key={`history-${entry.number}`} className="flex items-start gap-2 text-sm">
                <Badge variant="outline" className="text-xs shrink-0 font-mono">
                  {entry.number}
                </Badge>
                <div className="min-w-0">
                  <div className="font-medium">{cleanProgressText(entry.content)}</div>
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
