/**
 * SessionList - the signed-in user's connector sessions.
 *
 * @module components/sessions/SessionList
 * @version 1.0.0
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Terminal } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { SessionSummary } from '../../types/sessionTypes';

interface SessionListProps {
  sessions: SessionSummary[];
  selectedId: string | null;
  onSelect: (sessionId: string) => void;
}

// The server sends naive ISO timestamps (IsoFormatNaive); render them relative.
function relativeTime(value: string | null): string {
  if (!value) return 'never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'unknown';
  return formatDistanceToNow(date, { addSuffix: true });
}

export const SessionList: React.FC<SessionListProps> = ({ sessions, selectedId, onSelect }) => {
  if (sessions.length === 0) {
    return (
      <p className="p-4 text-sm text-base-secondary">
        No sessions yet. A runner holding a token with the <code>sessions:write</code> scope
        registers its sessions here.
      </p>
    );
  }

  return (
    <ul role="list" className="divide-y divide-surface-border-hover">
      {sessions.map((session) => {
        const isSelected = session.id === selectedId;
        return (
          <li key={session.id}>
            <button
              type="button"
              onClick={() => onSelect(session.id)}
              aria-current={isSelected ? 'true' : undefined}
              className={cn(
                'w-full px-4 py-3 text-left transition-colors',
                isSelected ? 'bg-primary/10' : 'hover:bg-primary/5'
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2 font-medium text-base-primary">
                  <Terminal className="h-4 w-4 shrink-0 text-teal-500" />
                  <span className="truncate">{session.name}</span>
                </span>
                <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>
                  {session.status}
                </Badge>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs text-base-secondary">
                <span className="truncate">{session.project ?? session.connector_id}</span>
                {/* The seat this session IS, from the row's own fields - the pair the message route
                    needs, so a rig's sessions are identifiable at a glance. Both come from the
                    connector at ingest; neither is derived from the name here, and a session whose
                    connector named no seat shows none rather than a guess. */}
                {session.seat_key && (
                  <Badge variant="outline" className="shrink-0 font-mono text-[10px]">
                    {session.room_slug ? `${session.room_slug}/${session.seat_key}` : session.seat_key}
                  </Badge>
                )}
                <span className="shrink-0">{relativeTime(session.last_seen)}</span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
};
