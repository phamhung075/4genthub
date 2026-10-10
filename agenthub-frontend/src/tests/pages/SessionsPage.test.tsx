/**
 * @fileoverview SessionsPage renders the user's session list and follows the
 * selected one over the live stream.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SessionsPage } from '../../pages/SessionsPage';
import { useSessionStream, useSessions } from '../../hooks/useSessions';
import type { SessionSummary } from '../../types/sessionTypes';

vi.mock('../../hooks/useSessions', () => ({
  useSessions: vi.fn(),
  useSessionStream: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ tokens: { access_token: 'tok' } }),
}));

const useSessionsMock = vi.mocked(useSessions);
const useSessionStreamMock = vi.mocked(useSessionStream);

const session = (
  id: string,
  name: string,
  seat: { room_slug: string | null; seat_key: string | null } = {
    room_slug: null,
    seat_key: null,
  }
): SessionSummary => ({
  id,
  name,
  project: 'proj',
  status: 'active',
  connector_id: 'conn-1',
  last_seq: 3,
  created_at: '2026-10-05T18:00:00',
  last_seen: '2026-10-05T18:00:00',
  room_slug: seat.room_slug,
  seat_key: seat.seat_key,
});

const renderPage = (path = '/sessions') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/sessions/:sessionId" element={<SessionsPage />} />
      </Routes>
    </MemoryRouter>
  );

describe('SessionsPage', () => {
  beforeEach(() => {
    useSessionsMock.mockReturnValue({
      sessions: [session('s1', 'alpha'), session('s2', 'beta')],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    useSessionStreamMock.mockReturnValue({ events: [], status: 'idle', error: null });
  });

  it('lists the sessions and follows the session named by the route', () => {
    renderPage('/sessions/s1');

    expect(screen.getByRole('heading', { name: 'Sessions' })).toBeInTheDocument();
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(useSessionStreamMock).toHaveBeenCalledWith('s1', 'tok');
  });

  it('opens a session on click and renders the events of its live stream', () => {
    useSessionStreamMock.mockImplementation((id) =>
      id === 's1'
        ? {
            events: [{ seq: 1, type: 'message', payload: 'hello from alpha', ts: null }],
            status: 'live',
            error: null,
          }
        : { events: [], status: 'idle', error: null }
    );

    renderPage('/sessions');
    expect(screen.getByText('Select a session to follow its live stream.')).toBeInTheDocument();

    fireEvent.click(screen.getByText('alpha'));

    expect(screen.getByText('hello from alpha')).toBeInTheDocument();
    expect(useSessionStreamMock).toHaveBeenCalledWith('s1', 'tok');
  });

  it('surfaces the terminal not-found stream error', () => {
    useSessionStreamMock.mockReturnValue({
      events: [],
      status: 'not-found',
      error: 'Session not found',
    });

    renderPage('/sessions/missing');

    expect(screen.getByText('Session not found')).toBeInTheDocument();
  });

  it('renders no chat input at all: phase 1 ships none, and the live window is the control', () => {
    // The ruled boundary (rigd-boundaries.md section 3): a browser session holding `sessions:write`
    // does NOT authorize a command - that needs `sessions:command`, a human-only issuer and a local
    // opt-in, which is phase 2. So this page mounts no input, and the POSITIVE CONTROL is the window
    // itself: an absence assertion against a page that rendered nothing would pass vacuously.
    useSessionsMock.mockReturnValue({
      sessions: [
        session('s1', 'web-dev@other-rig', { room_slug: '4genthub-min', seat_key: 'web-dev' }),
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    useSessionStreamMock.mockReturnValue({ events: [], status: 'live', error: null });

    renderPage('/sessions/s1');

    // The control: the window rendered, and this sentence is unique to it (it shows only while a
    // session is followed with no stored events).
    expect(screen.getByText('No events stored for this session yet.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Show message input' })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('renders a withheld event as the gap it is, with a delivered event beside it as the control', () => {
    // rigd fails CLOSED per event (rigd-boundaries.md 4.4): a withheld event is uploaded ONLY as
    // {type: "redaction_withheld", payload: {reason, bytes}} and carries no content and no hash of it.
    // The reason is rendered, because a reader has to be able to tell a gap from an empty event.
    useSessionStreamMock.mockImplementation((id) =>
      id === 's1'
        ? {
            events: [
              { seq: 1, type: 'message', payload: 'hello from alpha', ts: null },
              {
                seq: 2,
                type: 'redaction_withheld',
                payload: { reason: 'env_file', bytes: 412 },
                ts: null,
              },
            ],
            status: 'live',
            error: null,
          }
        : { events: [], status: 'idle', error: null }
    );

    renderPage('/sessions/s1');

    expect(screen.getByText('withheld locally: env_file')).toBeInTheDocument();
    // The control: the ordinary event in the same render is still shown as its content.
    expect(screen.getByText('hello from alpha')).toBeInTheDocument();
    // The placeholder is a GAP, not a payload dump: the generic renderer would print the JSON.
    expect(screen.queryByText(/\{"reason"/)).not.toBeInTheDocument();
  });

  it("shows each session's own seat, and invents none for a row the connector named none on", () => {
    // The rig's sessions are only identifiable as seats if the list shows the pair the session row
    // carries. Two rows, one of each shape, in the SAME render - the empty half is the control: a
    // list that derived a seat from the name would print one for `s2` too, whose name carries the
    // same `@rig` suffix and whose row is null.
    useSessionsMock.mockReturnValue({
      sessions: [
        session('s1', 'lead@4genthub-min', { room_slug: '4genthub-min', seat_key: 'lead' }),
        session('s2', 'web-dev@4genthub-min'),
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage('/sessions');

    expect(screen.getByText('4genthub-min/lead')).toBeInTheDocument();
    // `s2`'s name says `@4genthub-min` and its row says nothing, so no seat badge exists for it.
    expect(screen.getAllByText(/^4genthub-min\//)).toHaveLength(1);
    expect(screen.queryByText('4genthub-min/web-dev')).not.toBeInTheDocument();
  });

  it('shows a user with no sessions the empty state, and never a row the response did not carry', () => {
    // THE RIGHT-USER-ONLY HALF, at the only layer the browser owns it. The isolation itself is the
    // server's: `ListSessions` scopes by `WHERE user_id = $1` (session_stream/repository.go:361) with
    // the id taken from the BEARER TOKEN (server/routes/session_stream_routes.go:30), the session id
    // is derived per user (repository.go:53-54), and `/ws/sessions/{id}` answers 4004 for a session
    // that is not yours (pinned in useSessionStream.test.tsx). So this case asserts the browser's own
    // contribution: it lists EXACTLY what the user-scoped response carried and decides nothing itself.
    // Falsification: it fails the moment a row the response did not carry reaches this list - a
    // merged cache, a second source, or a client-side filter that keeps a foreign row alive.
    useSessionsMock.mockReturnValue({
      sessions: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    useSessionStreamMock.mockReturnValue({
      events: [],
      status: 'not-found',
      error: 'Session not found',
    });

    renderPage('/sessions/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee');

    expect(screen.getByText(/No sessions yet/)).toBeInTheDocument();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    // The followed id is one this user does not own, and the stream's refusal is what the page shows
    // for it - not a session row.
    expect(screen.getByText('Session not found')).toBeInTheDocument();
  });
});
