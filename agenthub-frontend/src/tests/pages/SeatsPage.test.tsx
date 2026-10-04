import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { SeatsPage } from '../../pages/SeatsPage';
import { seatApi } from '../../services/seatApi';
import { SEAT_MODEL_MESSAGE, SEAT_NAME_MESSAGE } from '../../lib/seatNames';

vi.mock('../../services/seatApi', () => ({
  seatApi: {
    listRooms: vi.fn(),
    createRoom: vi.fn(),
    listSeatTypes: vi.fn(),
    getModuleVersion: vi.fn(),
    listSeats: vi.fn(),
    createSeat: vi.fn(),
    removeSeat: vi.fn(),
    deleteRoom: vi.fn(),
    getOverlay: vi.fn(),
    putOverlay: vi.fn(),
    listLinks: vi.fn(),
    putLink: vi.fn(),
    getSettings: vi.fn(),
    putSettings: vi.fn(),
    getResolvedSeat: vi.fn(),
    fetchMachines: vi.fn(),
  },
}));

const mockApi = vi.mocked(seatApi);

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SeatsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const room = { id: 'room-1', slug: 'dev', name: 'Development' };

const seatType = {
  slug: 'coder',
  name: 'Coder',
  description: 'Writes code',
  default_runtime: 'claude-code',
  latest_version: '1.0.0',
  module_refs: [{ slug: 'rules', version: '1.0.0' }],
};

const iso = (minutesAgo: number) => new Date(Date.now() - minutesAgo * 60000).toISOString();

const machineSeat = {
  room: 'dev',
  seat: 'alice',
  state: 'running' as const,
  runtime: 'claude-code',
  hash: 'abcdef0123456789',
  expected_hash: 'abcdef0123456789',
  sync: 'in_sync' as const,
  detail: '<b>working</b>',
  redacted: false,
  reported_at: iso(1),
};

const machine = {
  machine_id: 'pc-home',
  last_seen: iso(5),
  online: true,
  seats: [machineSeat],
  agents: [{ agent: 'claude', status: 'idle' as const, pane_id: 'w5:p3' }],
};

const seat = {
  id: 'seat-1',
  room_id: 'room-1',
  seat_key: 'alice',
  seat_type: 'coder',
  pinned_version: '1.0.0',
  runtime: 'claude-code',
  model: 'sonnet',
};

describe('SeatsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.listRooms.mockResolvedValue({ success: true, rooms: [room] });
    mockApi.listSeatTypes.mockResolvedValue({ success: true, seat_types: [seatType] });
    mockApi.listSeats.mockResolvedValue({ success: true, seats: [seat] });
    mockApi.getSettings.mockResolvedValue({ success: true, settings: { follow_latest: false } });
    mockApi.fetchMachines.mockResolvedValue({ success: true, machines: [] });
    mockApi.createRoom.mockResolvedValue({
      success: true,
      room: { id: 'room-2', slug: 'eng', name: 'Engineering' },
    });
    mockApi.createSeat.mockResolvedValue({ success: true, seat });
    mockApi.removeSeat.mockResolvedValue({ success: true });
    mockApi.putSettings.mockResolvedValue({ success: true, settings: { follow_latest: true } });
  });

  it('renders the rooms and creates a room', async () => {
    renderPage();

    expect(await screen.findByText('Development')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Room slug'), { target: { value: 'eng' } });
    fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Engineering' } });
    fireEvent.click(screen.getByRole('button', { name: /create room/i }));

    await waitFor(() => {
      expect(mockApi.createRoom).toHaveBeenCalledWith({ slug: 'eng', name: 'Engineering' });
    });
  });

  it('creates a room and shows its seats', async () => {
    renderPage();
    await screen.findByText('Development');

    fireEvent.click(screen.getByRole('button', { name: /Development/ }));

    expect(await screen.findByText('alice')).toBeInTheDocument();
    expect(mockApi.listSeats).toHaveBeenCalledWith('dev');
    expect(screen.getAllByText('coder').length).toBeGreaterThan(0);
  });

  describe('delete room', () => {
    const openDeleteDialog = async () => {
      renderPage();
      fireEvent.click(await screen.findByRole('button', { name: /Development/ }));
      await screen.findByText('alice');
      fireEvent.click(screen.getByRole('button', { name: /delete room/i }));
      return screen.findByText('Delete room?');
    };

    it('deletes the selected room after confirmation and closes its seat list', async () => {
      mockApi.deleteRoom.mockResolvedValue({ success: true });
      const title = await openDeleteDialog();
      const dialog = title.closest('.theme-modal') as HTMLElement;
      expect(within(dialog).getByText(/Room "dev" is deleted with all of its seats/)).toBeInTheDocument();

      fireEvent.click(within(dialog).getByRole('button', { name: 'Delete room' }));

      await waitFor(() => expect(mockApi.deleteRoom).toHaveBeenCalledWith('dev'));
      await waitFor(() => expect(screen.queryByText('Seats in dev')).not.toBeInTheDocument());
      await waitFor(() => expect(mockApi.listRooms).toHaveBeenCalledTimes(2));
    });

    it('does not delete when the confirmation is cancelled', async () => {
      const title = await openDeleteDialog();
      const dialog = title.closest('.theme-modal') as HTMLElement;

      fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));

      await waitFor(() => expect(screen.queryByText('Delete room?')).not.toBeInTheDocument());
      expect(mockApi.deleteRoom).not.toHaveBeenCalled();
      expect(screen.getByText('Seats in dev')).toBeInTheDocument();
    });

    it('shows the server error and keeps the room when the delete fails', async () => {
      mockApi.deleteRoom.mockRejectedValue(new Error('room "dev" not found'));
      const title = await openDeleteDialog();
      const dialog = title.closest('.theme-modal') as HTMLElement;

      fireEvent.click(within(dialog).getByRole('button', { name: 'Delete room' }));

      expect(await within(dialog).findByText('room "dev" not found')).toBeInTheDocument();
      expect(screen.getByText('Seats in dev')).toBeInTheDocument();
    });
  });

  const openAddSeatDialog = async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Development/ }));
    await screen.findByText('alice');

    fireEvent.click(screen.getByRole('button', { name: /add seat/i }));

    const seatKey = await screen.findByLabelText('Seat key');
    fireEvent.change(seatKey, { target: { value: 'bob' } });
    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'sonnet' } });
    return screen;
  };

  const submitSeat = () => {
    const buttons = screen.getAllByRole('button', { name: /add seat/i });
    fireEvent.click(buttons[buttons.length - 1]);
  };

  it('posts follow_latest:false and no pinned_version when pinning to the latest', async () => {
    await openAddSeatDialog();
    fireEvent.click(screen.getByLabelText('Pin to latest'));
    submitSeat();

    await waitFor(() => {
      expect(mockApi.createSeat).toHaveBeenCalledWith('dev', {
        seat_key: 'bob',
        seat_type: 'coder',
        runtime: 'claude-code',
        model: 'sonnet',
        follow_latest: false,
      });
    });
    const body = mockApi.createSeat.mock.calls[0][1] as Record<string, unknown>;
    expect(body.pinned_version).toBeUndefined();
  });

  it('posts follow_latest:true and no pinned_version when following the latest', async () => {
    await openAddSeatDialog();
    fireEvent.click(screen.getByLabelText('Follow latest'));
    submitSeat();

    await waitFor(() => {
      expect(mockApi.createSeat).toHaveBeenCalledWith('dev', {
        seat_key: 'bob',
        seat_type: 'coder',
        runtime: 'claude-code',
        model: 'sonnet',
        follow_latest: true,
      });
    });
    const body = mockApi.createSeat.mock.calls[0][1] as Record<string, unknown>;
    expect(body.pinned_version).toBeUndefined();
  });

  it('omits both version fields when using the company default', async () => {
    await openAddSeatDialog();
    fireEvent.click(screen.getByLabelText('Use company default'));
    submitSeat();

    await waitFor(() => {
      expect(mockApi.createSeat).toHaveBeenCalledWith('dev', {
        seat_key: 'bob',
        seat_type: 'coder',
        runtime: 'claude-code',
        model: 'sonnet',
      });
    });
    const body = mockApi.createSeat.mock.calls[0][1] as Record<string, unknown>;
    expect(body.pinned_version).toBeUndefined();
    expect(body.follow_latest).toBeUndefined();
  });

  it('adds a seat with an empty model so the runtime default is used', async () => {
    await openAddSeatDialog();
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: '' } });
    fireEvent.click(screen.getByLabelText('Use company default'));
    submitSeat();

    await waitFor(() => {
      expect(mockApi.createSeat).toHaveBeenCalledWith('dev', {
        seat_key: 'bob',
        seat_type: 'coder',
        runtime: 'claude-code',
        model: '',
      });
    });
  });

  it('disables adding a seat and explains an invalid model id', async () => {
    await openAddSeatDialog();
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: '-bad model' } });

    const buttons = screen.getAllByRole('button', { name: /add seat/i });
    expect(buttons[buttons.length - 1]).toBeDisabled();
    expect(screen.getByText(SEAT_MODEL_MESSAGE)).toBeInTheDocument();
  });

  it('toggles the company follow-latest setting with PUT', async () => {
    renderPage();
    const toggle = await screen.findByLabelText('Follow latest by default');

    fireEvent.click(toggle);

    await waitFor(() => {
      expect(mockApi.putSettings).toHaveBeenCalledWith(true);
    });
  });

  it('blocks invalid room slugs and shows the name rule', async () => {
    renderPage();
    await screen.findByText('Development');

    fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Engineering' } });
    const slug = screen.getByLabelText('Room slug');

    for (const invalid of ['eng.one', 'eng one', '-eng']) {
      fireEvent.change(slug, { target: { value: invalid } });
      expect(screen.getByText(SEAT_NAME_MESSAGE)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create room/i })).toBeDisabled();
    }

    fireEvent.click(screen.getByRole('button', { name: /create room/i }));
    expect(mockApi.createRoom).not.toHaveBeenCalled();
  });

  it('accepts an uppercase room slug', async () => {
    renderPage();
    await screen.findByText('Development');

    fireEvent.change(screen.getByLabelText('Room slug'), { target: { value: 'Eng' } });
    fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Engineering' } });

    expect(screen.queryByText(SEAT_NAME_MESSAGE)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /create room/i }));

    await waitFor(() => {
      expect(mockApi.createRoom).toHaveBeenCalledWith({ slug: 'Eng', name: 'Engineering' });
    });
  });

  it('blocks invalid seat keys and accepts an uppercase key', async () => {
    await openAddSeatDialog();
    const seatKey = screen.getByLabelText('Seat key');
    const submit = () => {
      const buttons = screen.getAllByRole('button', { name: /add seat/i });
      return buttons[buttons.length - 1];
    };

    for (const invalid of ['bo.b', 'bo b', '-bob']) {
      fireEvent.change(seatKey, { target: { value: invalid } });
      expect(screen.getByText(SEAT_NAME_MESSAGE)).toBeInTheDocument();
      expect(submit()).toBeDisabled();
    }
    expect(mockApi.createSeat).not.toHaveBeenCalled();

    fireEvent.change(seatKey, { target: { value: 'Bob' } });
    expect(screen.queryByText(SEAT_NAME_MESSAGE)).not.toBeInTheDocument();
    fireEvent.click(submit());

    await waitFor(() => {
      expect(mockApi.createSeat).toHaveBeenCalledWith('dev', {
        seat_key: 'Bob',
        seat_type: 'coder',
        runtime: 'claude-code',
        model: 'sonnet',
      });
    });
  });

  describe('bridge machines', () => {
    it('shows the empty state when no bridge is connected', async () => {
      renderPage();
      expect(
        await screen.findByText('No bridge connected. Run scripts/openrig_bridge.py on your PC.')
      ).toBeInTheDocument();
    });

    it('renders online and offline machines with seats, short hash and agents', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          machine,
          { ...machine, machine_id: 'pc-work', online: false, last_seen: iso(120), seats: [], agents: [] },
        ],
      });
      renderPage();

      expect(await screen.findByText('pc-home')).toBeInTheDocument();
      expect(screen.getByText('online')).toBeInTheDocument();
      expect(screen.getByText('offline')).toBeInTheDocument();
      expect(screen.getByText('last seen 5 minutes ago')).toBeInTheDocument();
      expect(screen.getByText('last seen about 2 hours ago')).toBeInTheDocument();
      expect(screen.getByText('dev/alice')).toBeInTheDocument();
      expect(screen.getByText('running')).toBeInTheDocument();
      expect(screen.getByText('abcdef01')).toBeInTheDocument();
      expect(screen.getByText(/claude · idle · w5:p3/)).toBeInTheDocument();
    });

    it('renders detail as plain text and marks redacted seats', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [{ ...machine, seats: [{ ...machineSeat, redacted: true }] }],
      });
      renderPage();

      expect(await screen.findByText(/<b>working<\/b>/)).toBeInTheDocument();
      expect(screen.getByText('redacted')).toBeInTheDocument();
    });

    it('shows the most recently reported state on the seat row', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          machine,
          {
            ...machine,
            machine_id: 'pc-work',
            seats: [{ ...machineSeat, state: 'blocked' as const, reported_at: iso(10) }],
          },
          {
            ...machine,
            machine_id: 'pc-new',
            seats: [{ ...machineSeat, state: 'idle' as const, reported_at: iso(0) }],
          },
        ],
      });
      renderPage();
      await screen.findByText('pc-new');

      fireEvent.click(screen.getByRole('button', { name: /Development/ }));
      await screen.findByText('alice');
      // the panel shows each state once; the seat row adds only the newest report (idle)
      expect(screen.getAllByText('idle')).toHaveLength(2);
      expect(screen.getAllByText('blocked')).toHaveLength(1);
      expect(screen.getAllByText('running')).toHaveLength(1);
    });

    it('shows an in-sync badge with green classes and no drifted header badge', async () => {
      mockApi.fetchMachines.mockResolvedValue({ success: true, machines: [machine] });
      renderPage();

      const badge = await screen.findByText('in sync');
      expect(badge).toHaveClass('bg-green-50');
      expect(screen.queryByText(/drifted/)).not.toBeInTheDocument();
    });

    it('shows drift with the running and expected short hashes and amber classes', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          {
            ...machine,
            seats: [
              {
                ...machineSeat,
                hash: 'aaaaaaaa11111111',
                expected_hash: 'bbbbbbbb22222222',
                sync: 'drift' as const,
              },
            ],
          },
        ],
      });
      renderPage();

      const badge = await screen.findByText('drift · running aaaaaaaa · expected bbbbbbbb');
      expect(badge).toHaveClass('bg-amber-50');
    });

    it('shows sync unknown with neutral classes', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          { ...machine, seats: [{ ...machineSeat, expected_hash: '', sync: 'unknown' as const }] },
        ],
      });
      renderPage();

      const badge = await screen.findByText('sync unknown');
      expect(badge).not.toHaveClass('bg-green-50');
      expect(badge).not.toHaveClass('bg-amber-50');
    });

    it('counts drifted seats across machines and shows one badge per drifted row', async () => {
      const drifted = (seat: string, hash: string) => ({
        ...machineSeat,
        seat,
        hash,
        expected_hash: 'ffffffff00000000',
        sync: 'drift' as const,
      });
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          { ...machine, seats: [drifted('alice', 'aaaaaaaa11111111'), drifted('bob', 'bbbbbbbb22222222')] },
          { ...machine, machine_id: 'pc-work', seats: [drifted('carol', 'cccccccc33333333')] },
        ],
      });
      renderPage();

      expect(await screen.findByText('3 drifted')).toBeInTheDocument();
      expect(screen.getAllByText(/^drift ·/)).toHaveLength(3);
    });

    it('shows the latest reported sync badge on the selected room seat card', async () => {
      mockApi.fetchMachines.mockResolvedValue({
        success: true,
        machines: [
          {
            ...machine,
            machine_id: 'pc-old',
            seats: [{ ...machineSeat, reported_at: iso(10), sync: 'in_sync' as const }],
          },
          {
            ...machine,
            machine_id: 'pc-new',
            seats: [
              {
                ...machineSeat,
                reported_at: iso(0),
                hash: 'aaaaaaaa11111111',
                expected_hash: 'bbbbbbbb22222222',
                sync: 'drift' as const,
              },
            ],
          },
        ],
      });
      renderPage();
      await screen.findByText('pc-new');

      fireEvent.click(screen.getByRole('button', { name: /Development/ }));
      await screen.findByText('alice');

      // the panel shows both reports; the seat card adds only the latest (drift)
      expect(screen.getAllByText('drift · running aaaaaaaa · expected bbbbbbbb')).toHaveLength(2);
      expect(screen.getAllByText('in sync')).toHaveLength(1);
    });
  });

  describe('failed mutations', () => {
    it('shows the server error when creating a room fails', async () => {
      mockApi.createRoom.mockRejectedValue(new Error('room "eng" already exists'));
      renderPage();
      await screen.findByText('Development');

      fireEvent.change(screen.getByLabelText('Room slug'), { target: { value: 'eng' } });
      fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Engineering' } });
      fireEvent.click(screen.getByRole('button', { name: /create room/i }));

      expect(await screen.findByText('room "eng" already exists')).toBeInTheDocument();
      expect(screen.getByLabelText('Room slug')).toHaveValue('eng');
    });

    it('shows the server error and keeps the dialog open when adding a seat fails', async () => {
      mockApi.createSeat.mockRejectedValue(new Error('seat "bob" already exists'));
      await openAddSeatDialog();

      submitSeat();

      expect(await screen.findByText('seat "bob" already exists')).toBeInTheDocument();
      expect(screen.getByLabelText('Seat key')).toHaveValue('bob');
    });

    it('shows the server error and keeps the dialog open when removing a seat fails', async () => {
      mockApi.removeSeat.mockRejectedValue(new Error('seat "alice" not found'));
      renderPage();
      fireEvent.click(await screen.findByRole('button', { name: /Development/ }));
      await screen.findByText('alice');
      fireEvent.click(screen.getByRole('button', { name: 'Remove seat alice' }));
      const title = await screen.findByText('Remove seat?');
      const dialog = title.closest('.theme-modal') as HTMLElement;

      fireEvent.click(within(dialog).getByRole('button', { name: 'Remove seat' }));

      expect(await within(dialog).findByText('seat "alice" not found')).toBeInTheDocument();
      expect(screen.getByText('Remove seat?')).toBeInTheDocument();
    });
  });
});
