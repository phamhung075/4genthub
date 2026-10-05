/**
 * @fileoverview TopologyPage renders rooms as groups, seats as nodes and links
 * as edges drawn by kind, plus the seats table.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TopologyPage } from '../../pages/TopologyPage';
import { useTopology, type RoomTopology } from '../../hooks/useTopology';
import type { Seat, SeatLink } from '../../types/seatTypes';

vi.mock('../../hooks/useTopology', () => ({ useTopology: vi.fn() }));
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: () => ({ client: { on: vi.fn(), off: vi.fn() }, isConnected: false }),
}));
vi.mock('../../hooks/useRealtimeSync', () => ({ useRealtimeSync: vi.fn() }));
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' }, tokens: { access_token: 'tok' } }),
}));

const useTopologyMock = vi.mocked(useTopology);

const seat = (id: string, seatKey: string): Seat => ({
  id,
  room_id: 'room-dev',
  seat_key: seatKey,
  seat_type: 'developer',
  seat_type_id: 'type-1',
  pinned_version: null,
  runtime: 'omp',
  model: '',
  permission_policy: 'standard',
});

const link: SeatLink = {
  id: 'l1',
  from_seat_id: 'a',
  to_seat_id: 'b',
  kind: 'delegates_to',
  allow: true,
};

const topology: RoomTopology[] = [
  { room: { id: 'room-dev', slug: 'dev', name: 'Dev Room' }, seats: [seat('a', 'alice'), seat('b', 'bob')], links: [link] },
];

describe('TopologyPage', () => {
  beforeEach(() => {
    useTopologyMock.mockReturnValue({ rooms: topology, isLoading: false, error: null, refetch: vi.fn() });
  });

  it('draws each room as a group with its seats and an edge per link', () => {
    render(<TopologyPage />);

    expect(screen.getByRole('heading', { name: 'Topology' })).toBeInTheDocument();
    expect(screen.getByText('Dev Room')).toBeInTheDocument();
    expect(screen.getByText('dev · 2 seats')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();

    const edges = document.querySelectorAll('line[data-link-kind]');
    expect(edges).toHaveLength(1);
    expect(edges[0].getAttribute('data-link-kind')).toBe('delegates_to');
    expect(edges[0].getAttribute('data-link-allow')).toBe('true');

    // The legend names every kind so a colour on the canvas is readable.
    expect(screen.getByText('Gives work to')).toBeInTheDocument();
    expect(screen.getByText('Escalates to')).toBeInTheDocument();
  });

  it('shows every seat in the seats table with its type, runtime and policy', async () => {
    render(<TopologyPage />);

    await userEvent.click(screen.getByRole('tab', { name: 'Seats' }));

    expect(screen.getAllByRole('cell', { name: 'Dev Room' })).toHaveLength(2);
    expect(screen.getByRole('cell', { name: 'alice' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'bob' })).toBeInTheDocument();
    expect(screen.getAllByRole('cell', { name: 'developer' })).toHaveLength(2);
    expect(screen.getAllByRole('cell', { name: 'omp' })).toHaveLength(2);
    expect(screen.getAllByRole('cell', { name: 'standard' })).toHaveLength(2);
  });

  it('shows the empty state when there are no rooms', () => {
    useTopologyMock.mockReturnValue({ rooms: [], isLoading: false, error: null, refetch: vi.fn() });
    render(<TopologyPage />);

    expect(screen.getByText('No rooms yet. Create a room and add seats to see the topology.')).toBeInTheDocument();
  });
});
