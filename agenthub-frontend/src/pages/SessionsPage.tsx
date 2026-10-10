/**
 * Sessions Page - the signed-in user's sessions and one live event stream.
 *
 * The list comes from GET /api/v2/sessions; selecting a session opens
 * /ws/sessions/{id} through useSessionStream, which replays the stored events
 * before following the live ones. The raw-terminal (xterm) tab C3 marks
 * optional is not built: it would add a dependency the app does not carry.
 *
 * @module pages/SessionsPage
 * @version 1.0.0
 */

import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { SessionList } from '../components/sessions/SessionList';
import { SessionLiveView } from '../components/sessions/SessionLiveView';
import { useSessionStream, useSessions } from '../hooks/useSessions';
import { useAuth } from '../contexts/AuthContext';
import { cn } from '../lib/utils';

export const SessionsPage: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const { tokens } = useAuth();
  const { sessions, isLoading, error, refetch } = useSessions();
  const stream = useSessionStream(sessionId ?? null, tokens?.access_token ?? null);

  const selected = sessions.find((session) => session.id === sessionId) ?? null;

  // DERIVATION, NOT DATA: the room is read from the session name's `@rig` suffix. The suffix IS the
  // OpenRig rig name (ai_docs/core-architecture/agenthub-system-architecture.md:515) and this
  // deployment creates the agenthub room with the rig's own slug, so room-slug == rig-name and the
  // suffix names the room. Read it AS a derivation, not as a fact.
  // REVISIT CONDITION: the moment the session carries its room as real data, THIS LINE IS DELETED -
  // never kept as a fallback, so one concept never has two sources of truth.
  const room = selected?.name.split('@')[1] ?? null;

  return (
    <div className="mx-auto w-full max-w-6xl p-4 md:p-6">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-base-primary">Sessions</h1>
          <p className="text-sm text-base-secondary">
            Your connectors' sessions and the live event stream of the selected one.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn('mr-2 h-4 w-4', isLoading && 'animate-spin')} />
          Refresh
        </Button>
      </header>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            Could not load sessions: {error instanceof Error ? error.message : 'unknown error'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-[320px_1fr]">
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            {isLoading && sessions.length === 0 ? (
              <p className="p-4 text-sm text-base-secondary">Loading sessions…</p>
            ) : (
              <SessionList
                sessions={sessions}
                selectedId={sessionId ?? null}
                onSelect={(id) => navigate(`/sessions/${encodeURIComponent(id)}`)}
              />
            )}
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardContent className="h-[60vh] min-h-[320px] p-0">
            <SessionLiveView
              sessionName={selected?.name ?? null}
              events={stream.events}
              status={stream.status}
              error={stream.error}
              room={room}
              // The identifier this page holds is the session's name - the row's own seat fact.
              // Turning it into the route's `{seat_key}` is the route's decision, and it is this
              // one line if the answer differs from the name.
              seatKey={selected?.name ?? null}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
