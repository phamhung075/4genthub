/**
 * @fileoverview SeatPreview renders one seat's resolved snapshot from its {room, seat} PROPS.
 *
 * The props are REQUIRED and the component must not read them from the route: the preview is
 * rendered by the seat-detail page (/seats/:room/:seat) AND by the seat-authoring page
 * (/seats/authoring, which carries no such params). A component that called useParams would
 * therefore render an empty preview on the authoring page and read as a data bug, so the first
 * case renders it on a route WITHOUT the params and asserts the props drove the read.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeatPreview } from '../../components/seats/SeatPreview';
import { seatApi } from '../../services/seatApi';

vi.mock('../../services/seatApi', () => ({
  seatApi: { getResolvedSeat: vi.fn() },
}));

const mockApi = vi.mocked(seatApi);

const resolved = {
  room: 'dev',
  seat: 'alice',
  hash: 'abc123',
  runtime: 'omp',
  files: [
    { path: 'a.txt', content: 'A content' },
    { path: 'b.txt', content: 'B content' },
  ],
  policy: { allow: ['read'] },
};

// The route deliberately carries NO :room/:seat params, exactly like /seats/authoring.
const renderPreview = (room = 'dev', seat = 'alice') => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/seats/authoring']}>
        <Routes>
          <Route path="/seats/authoring" element={<SeatPreview room={room} seat={seat} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('SeatPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.getResolvedSeat.mockResolvedValue({ success: true, resolved_seat: resolved });
  });

  it('resolves from its PROPS on a route that carries no :room/:seat params', async () => {
    renderPreview();

    expect(await screen.findByText('abc123')).toBeInTheDocument();
    await waitFor(() => expect(mockApi.getResolvedSeat).toHaveBeenCalledWith('dev', 'alice'));
  });

  it('names the pull command and switches the shown file from the given room and seat', async () => {
    renderPreview('ops', 'bob');

    await waitFor(() => expect(mockApi.getResolvedSeat).toHaveBeenCalledWith('ops', 'bob'));
    expect(screen.getByText('4genteam sync pull ops bob')).toBeInTheDocument();

    expect(await screen.findByText('A content')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'b.txt' }));
    expect(screen.getByText('B content')).toBeInTheDocument();
  });

  it('reports a failed resolve instead of rendering an empty snapshot', async () => {
    mockApi.getResolvedSeat.mockRejectedValue(
      new Error('module queue-handoff@1.0.0 not found in catalog')
    );

    renderPreview();

    expect(
      await screen.findByText('module queue-handoff@1.0.0 not found in catalog')
    ).toBeInTheDocument();
  });
});
