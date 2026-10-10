/**
 * SessionLiveView - the live event stream of one session.
 *
 * Renders the events replayed and streamed by useSessionStream; each frame the
 * server sent is already a {seq, type, payload, ts} object.
 *
 * NO CHAT INPUT HERE, DELIBERATELY: phase 1 of the rigd slice ships none, and the ruled boundaries
 * (`ai_docs/core-architecture/rigd-boundaries.md`, section 3) make commands a phase-2 surface with
 * their own scope, a human-only issuer and a local opt-in - a browser session with `sessions:write`
 * does NOT authorize one. `SeatInputBox` stays in the tree for that phase; this view simply does not
 * mount it.
 *
 * @module components/sessions/SessionLiveView
 * @version 1.0.0
 */

import React from 'react';
import { AlertCircle, Loader2, Radio, ShieldAlert } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { SessionEvent } from '../../types/sessionTypes';
import type { SessionStreamStatus } from '../../hooks/useSessions';

interface SessionLiveViewProps {
  sessionName: string | null;
  events: SessionEvent[];
  status: SessionStreamStatus;
  error: string | null;
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

// Payloads are connector-defined JSON; show strings verbatim and objects as JSON.
function formatPayload(payload: unknown): string {
  if (payload === null || payload === undefined) return '';
  if (typeof payload === 'string') return payload;
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}

function statusBadgeVariant(status: SessionStreamStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'live') return 'default';
  if (status === 'error' || status === 'not-found') return 'destructive';
  return 'secondary';
}

export const SessionLiveView: React.FC<SessionLiveViewProps> = ({
  sessionName,
  events,
  status,
  error,
}) => {

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
          <p className="truncate text-xs text-base-secondary">{STATUS_LABEL[status]}</p>
        </div>
        <Badge variant={statusBadgeVariant(status)} className="ml-auto shrink-0">
          {STATUS_LABEL[status]}
        </Badge>
      </div>

      {(status === 'connecting' || status === 'reconnecting') && events.length === 0 && (
        <div className="flex items-center gap-2 p-4 text-sm text-base-secondary">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading stored events…
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 border-b border-surface-border-hover p-3 text-sm text-red-500">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {events.length === 0 && status !== 'connecting' && status !== 'reconnecting' ? (
          <p className="p-4 text-sm text-base-secondary">No events stored for this session yet.</p>
        ) : (
          <ul role="list">
            {events.map((event) => {
              // A withheld event arrives as {type: "redaction_withheld", payload: {reason, bytes}} and
              // carries no content and no hash of it (rigd-boundaries.md 4.4). It is rendered as the
              // GAP it is rather than as an event whose payload merely looks empty.
              const reason =
                event.type === 'redaction_withheld' &&
                event.payload !== null &&
                typeof event.payload === 'object' &&
                'reason' in event.payload &&
                typeof event.payload.reason === 'string'
                  ? event.payload.reason
                  : null;
              return (
                <li key={event.seq} className="border-b border-surface-border-hover px-4 py-2">
                  <div className="flex items-center gap-2 text-xs text-base-secondary">
                    <span className="font-mono">#{event.seq}</span>
                    <Badge variant="outline">{event.type}</Badge>
                    {event.ts && <span className="ml-auto truncate">{event.ts}</span>}
                  </div>
                  {reason === null ? (
                    <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-sm text-base-primary">
                      {formatPayload(event.payload)}
                    </pre>
                  ) : (
                    <p className="mt-1 flex items-center gap-2 text-sm text-amber-600 dark:text-amber-500">
                      <ShieldAlert className="h-4 w-4 shrink-0" />
                      withheld locally: {reason}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};
