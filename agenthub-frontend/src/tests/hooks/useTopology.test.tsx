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
import type { MachineEdge, MachinesResponse, Room, Seat, SeatLink } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: { listRooms: vi.fn(), listSeats: vi.fn(), listLinks: vi.fn(), fetchMachines: vi.fn() },
}));

const listRooms = vi.mocked(seatApi.listRooms);
const listSeats = vi.mocked(seatApi.listSeats);
const listLinks = vi.mocked(seatApi.listLinks);
const fetchMachines = vi.mocked(seatApi.fetchMachines);

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
    fetchMachines.mockReset();
    fetchMachines.mockResolvedValue({ success: true, machines: [] });

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
    expect(result.current.rooms[0].edges.map((e) => e.id)).toEqual(['l1']);
    expect(result.current.rooms[0].edgeSource).toBe('cloud');
    expect(result.current.rooms[1].room.slug).toBe('ops');
    expect(result.current.rooms[1].seats.map((s) => s.seat_key)).toEqual(['carol']);
    expect(result.current.rooms[1].edges).toEqual([]);
    // No machine is reporting in this case, so a room the cloud leaves edgeless says so rather than
    // claiming a machine report that does not exist.
    expect(result.current.rooms[1].edgeSource).toBe('none');

    // One links call per seat, addressed by room slug and seat key.
    expect(listLinks).toHaveBeenCalledWith('dev', 'alice');
    expect(listLinks).toHaveBeenCalledWith('dev', 'bob');
    expect(listLinks).toHaveBeenCalledWith('ops', 'carol');
    expect(listLinks).toHaveBeenCalledTimes(3);
  });

  // The selection rule, in the shapes that matter. The report is the only source for a room the cloud
  // leaves edgeless (the cloud refuses allow=true links on omp seats, so a running rig's real edges
  // exist only there), the cloud WINS when it has links, and the two are never concatenated.
  const twoSeatOps = async (slug: string) =>
    slug === 'dev'
      ? { success: true, seats: [seat('a', 'alice'), seat('b', 'bob')] }
      : { success: true, seats: [seat('c', 'carol'), seat('d', 'dave')] };

  const oneMachine = (online: boolean, edges: MachineEdge[]): MachinesResponse => ({
    success: true,
    machines: [
      { machine_id: 'pc-1', last_seen: '2026-10-09T19:00:00Z', online, seats: [], agents: [], edges },
    ],
  });

  it('draws a room with no cloud links from the online machine report, and never blends the two sources', async () => {
    listSeats.mockImplementation(twoSeatOps);
    fetchMachines.mockResolvedValue(
      oneMachine(true, [
        { room: 'ops', from: 'carol', to: 'dave', kind: 'escalates_to' },
        { room: 'dev', from: 'alice', to: 'bob', kind: 'escalates_to' },
      ])
    );

    const { result } = renderHook(() => useTopology(), { wrapper });
    await waitFor(() => expect(result.current.rooms).toHaveLength(2));

    const [dev, ops] = result.current.rooms;

    // dev HAS cloud links, so it is drawn from them and NOT from the report - the report's dev edge is
    // ignored rather than added, which is the difference between a selection and a merge.
    expect(dev.edgeSource).toBe('cloud');
    expect(dev.edges.map((e) => e.id)).toEqual(['l1']);
    expect(dev.edges.map((e) => e.kind)).toEqual(['delegates_to']);

    // ops has no cloud links, so the report's edge for it is what is drawn - by seat ID, resolved from
    // the report's seat KEYS, and with `allow` null rather than a flag the report never sent.
    expect(ops.edgeSource).toBe('report');
    expect(ops.edges).toEqual([
      {
        id: 'report:ops:carol:dave:escalates_to:0',
        from_seat_id: 'c',
        to_seat_id: 'd',
        kind: 'escalates_to',
        allow: null,
      },
    ]);
  });

  it('ignores an OFFLINE machine, whose last report is not the rig running now', async () => {
    listSeats.mockImplementation(twoSeatOps);
    fetchMachines.mockResolvedValue(
      oneMachine(false, [{ room: 'ops', from: 'carol', to: 'dave', kind: 'delegates_to' }])
    );

    const { result } = renderHook(() => useTopology(), { wrapper });
    await waitFor(() => expect(result.current.rooms).toHaveLength(2));

    expect(result.current.rooms[1].edges).toEqual([]);
    expect(result.current.rooms[1].edgeSource).toBe('none');
  });

  it('drops a report edge naming a seat this room does not have, but still calls the report the source', async () => {
    listSeats.mockImplementation(twoSeatOps);
    fetchMachines.mockResolvedValue(
      oneMachine(true, [{ room: 'ops', from: 'carol', to: 'ghost', kind: 'delegates_to' }])
    );

    const { result } = renderHook(() => useTopology(), { wrapper });
    await waitFor(() => expect(result.current.rooms).toHaveLength(2));

    // An edge to a node that does not exist cannot be drawn. A machine IS reporting, so the source is
    // still the report - calling it 'none' would overstate the absence.
    expect(result.current.rooms[1].edges).toEqual([]);
    expect(result.current.rooms[1].edgeSource).toBe('report');
  });
});
