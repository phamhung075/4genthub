import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { SeatDetailPage } from '../../pages/SeatDetailPage';
import { seatApi } from '../../services/seatApi';
import type { SeatOverlay, SeatOverlayScope } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: {
    listRooms: vi.fn(),
    createRoom: vi.fn(),
    listSeatTypes: vi.fn(),
    getModuleVersion: vi.fn(),
    listSeats: vi.fn(),
    createSeat: vi.fn(),
    removeSeat: vi.fn(),
    getOverlay: vi.fn(),
    putOverlay: vi.fn(),
    listLinks: vi.fn(),
    putLink: vi.fn(),
    getSettings: vi.fn(),
    putSettings: vi.fn(),
    getResolvedSeat: vi.fn(),
  },
}));

const mockApi = vi.mocked(seatApi);

const renderDetail = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/seats/dev/alice']}>
        <Routes>
          <Route path="/seats/:room/:seat" element={<SeatDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const seatTypes = [
  {
    slug: 'coder',
    name: 'Coder',
    description: 'Writes code',
    default_runtime: 'claude-code',
    latest_version: '1.0.0',
    module_refs: [{ slug: 'rules', version: '1.0.0' }],
  },
];

const seats = [
  {
    id: 'seat-1',
    room_id: 'room-1',
    seat_key: 'alice',
    seat_type: 'coder',
    pinned_version: '1.0.0',
    runtime: 'claude-code',
    model: 'sonnet',
    status: 'active',
  },
  {
    id: 'seat-2',
    room_id: 'room-1',
    seat_key: 'bob',
    seat_type: 'coder',
    pinned_version: null,
    runtime: 'codex',
    model: 'gpt',
    status: 'active',
  },
];

const existingOp = { kind: 'add' as const, slug: 'base', version: '1.0.0', content: '' };

const overlayFor = (scope: SeatOverlayScope, ops: SeatOverlay['ops'] = []): SeatOverlay => ({
  scope,
  ops,
});

describe('SeatDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.listSeats.mockResolvedValue({ success: true, seats });
    mockApi.listSeatTypes.mockResolvedValue({ success: true, seat_types: seatTypes });
    mockApi.getModuleVersion.mockImplementation(async (slug: string, version: string) => ({
      success: true,
      module: { slug, kind: 'instruction' as const, version, content: `${slug} content`, checksum: 'x' },
    }));
    mockApi.getOverlay.mockImplementation(async (scope: SeatOverlayScope) => ({
      success: true,
      overlay: overlayFor(scope, scope === 'seat' ? [existingOp] : []),
    }));
    mockApi.putOverlay.mockResolvedValue({ success: true, overlay: overlayFor('seat') });
    mockApi.listLinks.mockResolvedValue({
      success: true,
      links: [
        { id: 'l1', from_seat_id: 'seat-1', to_seat_id: 'seat-2', kind: 'delegates_to', allow: true },
      ],
    });
    mockApi.putLink.mockResolvedValue({
      success: true,
      link: { id: 'l1', from_seat_id: 'seat-1', to_seat_id: 'seat-2', kind: 'delegates_to', allow: false },
    });
    mockApi.getResolvedSeat.mockResolvedValue({
      success: true,
      resolved_seat: {
        room: 'dev',
        seat: 'alice',
        hash: 'abc123',
        runtime: 'claude-code',
        files: [
          { path: 'a.md', content: 'A content' },
          { path: 'b.txt', content: 'B content' },
        ],
        policy: { max_turns: 5 },
      },
    });
  });

  const openModules = async () => {
    renderDetail();
    await screen.findByText('rules');
  };

  it('builds the full ordered ops list for add, remove, override and pin and deletes an op', async () => {
    await openModules();

    // add
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'add' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'extra' } });
    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '2.0.0' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        1,
        'seat',
        { ops: [existingOp, { kind: 'add', slug: 'extra', version: '2.0.0', content: '' }] },
        'dev',
        'alice'
      );
    });

    // remove
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'remove' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        2,
        'seat',
        { ops: [existingOp, { kind: 'remove', slug: 'base', version: '', content: '' }] },
        'dev',
        'alice'
      );
    });

    // override
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'override' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.change(screen.getByLabelText('Content'), { target: { value: 'new content' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        3,
        'seat',
        { ops: [existingOp, { kind: 'override', slug: 'base', version: '', content: 'new content' }] },
        'dev',
        'alice'
      );
    });

    // pin
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'pin' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '1.2.3' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        4,
        'seat',
        { ops: [existingOp, { kind: 'pin', slug: 'base', version: '1.2.3', content: '' }] },
        'dev',
        'alice'
      );
    });

    // delete op 1 leaves the ordered list without it
    fireEvent.click(screen.getByLabelText('Delete op 1'));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(5, 'seat', { ops: [] }, 'dev', 'alice');
    });
  });

  it('toggles a link allow flag', async () => {
    renderDetail();
    await screen.findByText('rules');

    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    const toggle = await screen.findByLabelText('Allow bob (delegates_to)');
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(mockApi.putLink).toHaveBeenCalledWith('dev', 'alice', {
        to_seat: 'bob',
        kind: 'delegates_to',
        allow: false,
      });
    });
  });

  it('shows the resolved hash and switches files', async () => {
    renderDetail();
    await screen.findByText('rules');

    fireEvent.mouseDown(screen.getByRole('tab', { name: /preview/i }), { button: 0 });

    expect(await screen.findByText('abc123')).toBeInTheDocument();
    expect(screen.getByText('A content')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'b.txt' }));

    expect(screen.getByText('B content')).toBeInTheDocument();
  });
});
