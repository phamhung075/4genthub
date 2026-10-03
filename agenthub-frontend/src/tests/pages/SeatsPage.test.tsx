import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { SeatsPage } from '../../pages/SeatsPage';
import { seatApi } from '../../services/seatApi';
import { SEAT_NAME_MESSAGE } from '../../lib/seatNames';

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

const seat = {
  id: 'seat-1',
  room_id: 'room-1',
  seat_key: 'alice',
  seat_type: 'coder',
  pinned_version: '1.0.0',
  runtime: 'claude-code',
  model: 'sonnet',
  status: 'active',
};

describe('SeatsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.listRooms.mockResolvedValue({ success: true, rooms: [room] });
    mockApi.listSeatTypes.mockResolvedValue({ success: true, seat_types: [seatType] });
    mockApi.listSeats.mockResolvedValue({ success: true, seats: [seat] });
    mockApi.getSettings.mockResolvedValue({ success: true, settings: { follow_latest: false } });
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
});
