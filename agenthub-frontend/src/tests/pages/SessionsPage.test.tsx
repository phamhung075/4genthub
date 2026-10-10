/**
 * @fileoverview SessionsPage renders the user's session list and follows the
 * selected one over the live stream.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SessionsPage } from '../../pages/SessionsPage';
import { useSessionStream, useSessions } from '../../hooks/useSessions';
import { seatApi } from '../../services/seatApi';
import type { SessionSummary } from '../../types/sessionTypes';

vi.mock('../../hooks/useSessions', () => ({
  useSessions: vi.fn(),
  useSessionStream: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ tokens: { access_token: 'tok' } }),
}));

// The send is the only observable of what the page hands the window: the chat input addresses
// whatever pair it is given, so the route it posts to is the page's decision, not the input's.
vi.mock('../../services/seatApi', () => ({
  seatApi: { sendSeatMessage: vi.fn() },
}));

const useSessionsMock = vi.mocked(useSessions);
const useSessionStreamMock = vi.mocked(useSessionStream);
const mockSeatApi = vi.mocked(seatApi);

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

// A provider, because the window now holds a real mutation: the chat input's send. This file mocks
// the two query hooks, so before the input existed no QueryClient was needed here at all - the
// component that needs one now is the one under test's own child.
const renderPage = (path = '/sessions') => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/sessions/:sessionId" element={<SessionsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('SessionsPage', () => {
  beforeEach(() => {
    useSessionsMock.mockReturnValue({
      sessions: [session('s1', 'alpha'), session('s2', 'beta')],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    useSessionStreamMock.mockReturnValue({ events: [], status: 'idle', error: null });
    mockSeatApi.sendSeatMessage.mockResolvedValue({ success: true });
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

  it("sends to the room and seat the session's own row carries, not to what its name says", async () => {
    // The name reads `@other-rig` while the session's own row says `4genthub-min` / `web-dev`. A page
    // that parsed the name would post into another room and would do it silently, which is the
    // failure the (room, seat_key) pair - and this case - exist to make impossible.
    useSessionsMock.mockReturnValue({
      sessions: [
        session('s1', 'web-dev@other-rig', { room_slug: '4genthub-min', seat_key: 'web-dev' }),
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    // A live stream, because the window renders no chat input while no session is followed - and a
    // case that observed the absence under `idle` would pass whether or not the pair was used.
    useSessionStreamMock.mockReturnValue({ events: [], status: 'live', error: null });

    renderPage('/sessions/s1');
    fireEvent.click(screen.getByRole('button', { name: 'Show message input' }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '  hello  ' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() =>
      expect(mockSeatApi.sendSeatMessage).toHaveBeenCalledWith('4genthub-min', 'web-dev', {
        text: 'hello',
      })
    );
  });

  it('renders no chat input when the session carries no seat, though its name has an @rig suffix', () => {
    // The derivation that stood here read the room `4genthub-min` out of this very name and passed
    // the name itself as the seat key, so an input WOULD have rendered. The pair is null, so the
    // window stays watch-only instead of posting into a room it would have to guess.
    useSessionsMock.mockReturnValue({
      sessions: [session('s1', 'web-dev@4genthub-min')],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    // Live for the same reason as the case above: under `idle` the window is replaced wholesale, so
    // the absence of the input would prove nothing about the pair.
    useSessionStreamMock.mockReturnValue({ events: [], status: 'live', error: null });

    renderPage('/sessions/s1');

    expect(screen.queryByRole('button', { name: 'Show message input' })).not.toBeInTheDocument();
  });
});
