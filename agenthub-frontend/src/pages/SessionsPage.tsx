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

  // THE SEAT'S IDENTITY IS THE SESSION'S OWN DATA, and this is where the `@rig` derivation stood:
  // its own revisit condition - "the moment the session carries its room as real data" - is MET, so
  // the line is DELETED rather than kept as a fallback, and one concept keeps one source of truth.
  // Both facts arrive on the session row from the columns the connector wrote at ingest, serialized
  // by GET /api/v2/sessions (`sessionRow` in agenthub_go/fastmcp/session_stream/repository.go; the
  // wire case over the decoded body is fastmcp/server/httpapp/ws_connector_test.go). NO FALLBACK: a
  // session whose connector named no seat carries null here and gets no chat input, because a room
  // guessed from the name posts to the wrong room silently - which is what the (room, seat_key)
  // pair rules out.
  const room = selected?.room_slug ?? null;

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
              // The seat key is the session's own field, passed straight through. The name is not
              // an identifier for the route, and parsing it would be the guessing this replaces.
              seatKey={selected?.seat_key ?? null}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
