/**
 * @fileoverview useTopology folds the rooms, seats and links routes into one
 * query: one links call per seat, every room carrying its own nodes and edges.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { createTestQueryClient } from '../query-utils';
import { topologyKeys, useTopology } from '../../hooks/useTopology';
import { seatApi } from '../../services/seatApi';
import type { Room, Seat, SeatLink } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: { listRooms: vi.fn(), listSeats: vi.fn(), listLinks: vi.fn() },
}));

const listRooms = vi.mocked(seatApi.listRooms);
const listSeats = vi.mocked(seatApi.listSeats);
const listLinks = vi.mocked(seatApi.listLinks);

const room = (slug: string, name: string): Room => ({ id: `room-${slug}`, slug, name });

const seat = (id: string, seatKey: string): Seat => ({
  id,
  room_id: 'room-dev',
  seat_key: seatKey,
  seat_type: 'developer',
  seat_type_id: 'type-1',
  pinned_version: '1.0.0',
  runtime: 'omp',
  model: '',
  permission_policy: 'standard',
});

const link = (id: string, from: string, to: string): SeatLink => ({
  id,
  from_seat_id: from,
  to_seat_id: to,
  kind: 'delegates_to',
  allow: true,
});

describe('useTopology', () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    queryClient = createTestQueryClient();
    listRooms.mockReset();
    listSeats.mockReset();
    listLinks.mockReset();

    listRooms.mockResolvedValue({ success: true, rooms: [room('dev', 'Dev Room'), room('ops', 'Ops Room')] });
    listSeats.mockImplementation(async (slug: string) =>
      slug === 'dev'
        ? { success: true, seats: [seat('a', 'alice'), seat('b', 'bob')] }
        : { success: true, seats: [seat('c', 'carol')] }
    );
    listLinks.mockImplementation(async (slug: string, seatKey: string) =>
      slug === 'dev' && seatKey === 'alice'
        ? { success: true, links: [link('l1', 'a', 'b')] }
        : { success: true, links: [] }
    );
  });

  it('exposes the composite key the realtime handler invalidates', () => {
    expect(topologyKeys.all).toEqual(['seatTopology']);
  });

  it('folds rooms, seats and one links call per seat into the room entries', async () => {
    const { result } = renderHook(() => useTopology(), { wrapper });

    await waitFor(() => expect(result.current.rooms).toHaveLength(2));

    expect(result.current.rooms[0].room.slug).toBe('dev');
    expect(result.current.rooms[0].seats.map((s) => s.seat_key)).toEqual(['alice', 'bob']);
    expect(result.current.rooms[0].links.map((l) => l.id)).toEqual(['l1']);
    expect(result.current.rooms[1].room.slug).toBe('ops');
    expect(result.current.rooms[1].seats.map((s) => s.seat_key)).toEqual(['carol']);
    expect(result.current.rooms[1].links).toEqual([]);

    // One links call per seat, addressed by room slug and seat key.
    expect(listLinks).toHaveBeenCalledWith('dev', 'alice');
    expect(listLinks).toHaveBeenCalledWith('dev', 'bob');
    expect(listLinks).toHaveBeenCalledWith('ops', 'carol');
    expect(listLinks).toHaveBeenCalledTimes(3);
  });
});
