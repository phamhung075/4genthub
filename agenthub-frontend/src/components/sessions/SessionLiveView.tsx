/**
 * SessionLiveView - the live event stream of one session.
 *
 * Renders the events replayed and streamed by useSessionStream as steps (sessionSteps):
 * the user's message, the assistant's text, its thinking, each tool call with its
 * arguments and each tool result, in the order they happened. Long bodies and
 * arguments are collapsed, and older history loads on request.
 *
 * NO CHAT INPUT HERE, DELIBERATELY: phase 1 of the agent slice ships none, and the ruled boundaries
 * (`ai_docs/core-architecture/agent-boundaries.md`, section 3) make commands a phase-2 surface with
 * their own scope, a human-only issuer and a local opt-in - a browser session with `sessions:write`
 * does NOT authorize one. `SeatInputBox` stays in the tree for that phase; this view simply does not
 * mount it.
 *
 * @module components/sessions/SessionLiveView
 * @version 1.0.0
 */

import React, { useEffect, useMemo, useRef } from 'react';
import {
  AlertCircle,
  Brain,
  ChevronRight,
  Info,
  Loader2,
  Radio,
  ShieldAlert,
  SquareTerminal,
  Terminal,
  User,
  Bot,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import type { SessionEvent } from '../../types/sessionTypes';
import type { SessionStreamStatus } from '../../hooks/useSessions';
import {
  sessionSteps,
  type LogicSchema,
  type SessionStep,
  type SessionStepKind,
} from '../../utils/sessionSteps';

interface SessionLiveViewProps {
  sessionName: string | null;
  events: SessionEvent[];
  status: SessionStreamStatus;
  error: string | null;
  hasOlder: boolean;
  loadingOlder: boolean;
  onLoadOlder: () => void;
}

const STATUS_LABEL: Record<SessionStreamStatus, string> = {
  idle: 'no session selected',
  connecting: 'connecting…',
  live: 'live',
  reconnecting: 'reconnecting…',
  'not-found': 'not found',
  closed: 'closed',
  error: 'error',
};

function statusBadgeVariant(status: SessionStreamStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'live') return 'default';
  if (status === 'error' || status === 'not-found') return 'destructive';
  return 'secondary';
}

const KIND_STYLE: Record<SessionStepKind, { icon: React.ElementType; rail: string; label: string }> = {
  user: { icon: User, rail: 'border-l-blue-500', label: 'text-blue-600 dark:text-blue-400' },
  assistant: { icon: Bot, rail: 'border-l-emerald-500', label: 'text-emerald-600 dark:text-emerald-400' },
  thinking: { icon: Brain, rail: 'border-l-violet-400', label: 'text-violet-600 dark:text-violet-400' },
  tool_call: { icon: Terminal, rail: 'border-l-amber-500', label: 'text-amber-600 dark:text-amber-400' },
  tool_result: { icon: SquareTerminal, rail: 'border-l-slate-400', label: 'text-base-secondary' },
  meta: { icon: Info, rail: 'border-l-transparent', label: 'text-base-secondary' },
  withheld: { icon: ShieldAlert, rail: 'border-l-amber-500', label: 'text-amber-600 dark:text-amber-500' },
  text: { icon: Terminal, rail: 'border-l-slate-400', label: 'text-base-secondary' },
};

// A body longer than this many lines opens collapsed behind its first lines.
const PREVIEW_LINES = 8;

function formatTime(ts: string | null): string {
  if (!ts) return '';
  const date = new Date(ts.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts}Z`);
  return Number.isNaN(date.getTime()) ? ts : date.toLocaleTimeString();
}

const Body: React.FC<{ text: string; mono?: boolean }> = ({ text, mono }) => {
  const lines = text.split('\n');
  const long = lines.length > PREVIEW_LINES;
  const className = cn(
    'whitespace-pre-wrap break-words text-sm text-base-primary',
    mono && 'font-mono text-xs',
  );
  if (!long) return <pre className={className}>{text}</pre>;
  return (
    <details className="group">
      <summary className="cursor-pointer list-none">
        <pre className={cn(className, 'group-open:hidden')}>{lines.slice(0, PREVIEW_LINES).join('\n')}</pre>
        <span className="text-xs text-base-secondary group-open:hidden">
          … {lines.length - PREVIEW_LINES} more lines
        </span>
        <span className="hidden text-xs text-base-secondary group-open:inline">Collapse</span>
      </summary>
      <pre className={className}>{text}</pre>
    </details>
  );
};

// The four fields a thinking step carries, in the schema's pinned order. Compact on purpose: one row
// per field, the key in mono, the value in the reading face.
const LOGIC_FIELDS: Array<keyof LogicSchema> = ['facts', 'rule', 'decision', 'next'];

const LogicSchemaView: React.FC<{ schema: LogicSchema }> = ({ schema }) => (
  <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1">
    {LOGIC_FIELDS.map((field) => (
      <React.Fragment key={field}>
        <dt className="font-mono text-xs leading-5 text-violet-600 dark:text-violet-400">{field}</dt>
        <dd className="whitespace-pre-wrap break-words text-sm leading-5 text-base-primary">
          {schema[field]}
        </dd>
      </React.Fragment>
    ))}
  </dl>
);

const StepCard: React.FC<{ step: SessionStep }> = ({ step }) => {
  const style = KIND_STYLE[step.kind];
  const Icon = style.icon;

  // Session bookkeeping (model change, title, …) is one muted line, not a card.
  if (step.kind === 'meta') {
    return (
      <li className="flex items-center gap-2 px-4 py-1 text-xs text-base-secondary">
        <Icon className="h-3 w-3 shrink-0" />
        <span className="capitalize">{step.title}</span>
        {step.body && <span className="truncate font-mono">{step.body}</span>}
        <span className="ml-auto shrink-0">{formatTime(step.ts)}</span>
      </li>
    );
  }

  return (
    <li className="px-3 py-1.5">
      <div
        className={cn(
          'rounded-md border border-l-4 border-surface-border-hover bg-surface px-3 py-2',
          style.rail,
          step.isError && 'border-l-red-500',
        )}
      >
        <div className="mb-1 flex items-center gap-2 text-xs">
          <Icon className={cn('h-3.5 w-3.5 shrink-0', style.label)} />
          <span className={cn('font-medium', style.label, step.isError && 'text-red-500')}>
            {step.title}
          </span>
          {step.kind === 'tool_call' && step.body && (
            <span className="truncate text-base-secondary">{step.body}</span>
          )}
          {step.isError && <Badge variant="destructive">error</Badge>}
          <span className="ml-auto shrink-0 text-base-secondary">
            {formatTime(step.ts)} · #{step.seq}
          </span>
        </div>

        {step.kind === 'withheld' ? (
          <p className="text-sm text-amber-600 dark:text-amber-500">
            Content withheld on the machine that ran it{step.body ? `: ${step.body}` : ''}.
          </p>
        ) : step.kind === 'thinking' ? (
          <>
            {step.logic && <LogicSchemaView schema={step.logic} />}
            <details className={step.logic ? 'mt-1' : undefined}>
              <summary className="flex cursor-pointer list-none items-center gap-1 text-xs text-base-secondary">
                <ChevronRight className="h-3 w-3" /> Show reasoning
              </summary>
              <div className="mt-1 italic text-base-secondary">
                <Body text={step.body} />
              </div>
            </details>
          </>
        ) : step.kind === 'tool_call' ? (
          step.detail ? (
            <details>
              <summary className="flex cursor-pointer list-none items-center gap-1 text-xs text-base-secondary">
                <ChevronRight className="h-3 w-3" /> Arguments
              </summary>
              <div className="mt-1">
                <Body text={step.detail} mono />
              </div>
            </details>
          ) : null
        ) : step.kind === 'tool_result' ? (
          step.body ? <Body text={step.body} mono /> : <p className="text-xs text-base-secondary">No output.</p>
        ) : (
          <Body text={step.body} />
        )}
      </div>
    </li>
  );
};

export const SessionLiveView: React.FC<SessionLiveViewProps> = ({
  sessionName,
  events,
  status,
  error,
  hasOlder,
  loadingOlder,
  onLoadOlder,
}) => {
  const steps = useMemo(() => sessionSteps(events), [events]);
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const newestSeq = events.length > 0 ? events[events.length - 1].seq : 0;
  const oldestSeq = events.length > 0 ? events[0].seq : 0;
  const atStart = oldestSeq === 0;

  // Follow the newest step while the reader is at the bottom; reading history leaves the scroll alone.
  useEffect(() => {
    const node = scroller.current;
    if (node && stickToBottom.current) node.scrollTop = node.scrollHeight;
  }, [newestSeq, atStart]);

  if (status === 'idle') {
    return (
      <div className="flex h-full items-center justify-center p-8 text-sm text-base-secondary">
        Select a session to follow its live stream.
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-3 border-b border-surface-border-hover px-4 py-3">
        <Radio
          className={cn('h-4 w-4 shrink-0', status === 'live' ? 'text-green-500' : 'text-base-secondary')}
        />
        <div className="min-w-0">
          <p className="truncate font-medium text-base-primary">{sessionName ?? 'Session'}</p>
          <p className="truncate text-xs text-base-secondary">{steps.length} steps shown</p>
        </div>
        <Badge variant={statusBadgeVariant(status)} className="ml-auto shrink-0">
          {STATUS_LABEL[status]}
        </Badge>
      </div>

      {(status === 'connecting' || status === 'reconnecting') && events.length === 0 && (
        <div className="flex items-center gap-2 p-4 text-sm text-base-secondary">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading recent events…
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 border-b border-surface-border-hover p-3 text-sm text-red-500">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div
        ref={scroller}
        className="min-h-0 flex-1 overflow-y-auto"
        onScroll={(event) => {
          const node = event.currentTarget;
          stickToBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
        }}
      >
        {events.length === 0 && status !== 'connecting' && status !== 'reconnecting' ? (
          <p className="p-4 text-sm text-base-secondary">No events stored for this session yet.</p>
        ) : (
          <>
            {hasOlder && (
              <div className="flex justify-center p-2">
                <Button variant="outline" size="sm" onClick={onLoadOlder} disabled={loadingOlder}>
                  {loadingOlder ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : null}
                  Load older events
                </Button>
              </div>
            )}
            <ul role="list">
              {steps.map((step) => (
                <StepCard key={step.key} step={step} />
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
};
