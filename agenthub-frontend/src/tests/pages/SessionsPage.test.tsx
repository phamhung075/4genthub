/**
 * @fileoverview SessionsPage renders the user's session list and follows the
 * selected one over the live stream.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

const session = (id: string, name: string): SessionSummary => ({
  id,
  name,
  project: 'proj',
  status: 'active',
  connector_id: 'conn-1',
  last_seq: 3,
  created_at: '2026-10-05T18:00:00',
  last_seen: '2026-10-05T18:00:00',
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
});
