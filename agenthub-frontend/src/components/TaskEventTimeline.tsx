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
import type { TaskEvent } from '../types/taskTypes';

export interface TaskEventTimelineProps {
  /**
   * The task whose ledger to render.
   *
   * THERE IS DELIBERATELY NO STATUS PROP: the phase is derived from the events and never read from
   * the task, and taking only an id is what makes that true by construction rather than by promise.
   */
  taskId: string | undefined;
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
 * The task's EXECUTION LEDGER (`task_events`) as a timeline.
 *
 * The badge above the list is `deriveLedgerPhase(events)` - a fold over the sequence, not a field -
 * so a task whose stored status and ledger disagree shows the LEDGER's phase. What the vocabulary
 * cannot express is stated under the list rather than dressed up: a status change to `testing` or
 * `review` is not evidence that a test passed (see `LEDGER_NOT_RECORDED`).
 */
export const TaskEventTimeline: React.FC<TaskEventTimelineProps> = ({ taskId, className = '' }) => {
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

      {events.length === 0 ? (
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
          </ol>
          <p className="text-xs text-muted-foreground mt-3">{LEDGER_NOT_RECORDED}</p>
        </>
      )}
    </div>
  );
};
