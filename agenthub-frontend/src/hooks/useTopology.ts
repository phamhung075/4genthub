/**
 * Topology Hooks - the whole workspace as rooms, seats and edges in one query.
 *
 * F6 reads the existing routes and folds them into one shape: rooms
 * (`GET /api/v2/openrig/rooms`), seats per room (`/rooms/{room}/seats`) and
 * links per seat (`/rooms/{room}/seats/{seat}/links`, which returns the links
 * FROM that seat, so one call per seat covers every cloud edge). It is one React
 * Query key so the realtime seat handler can invalidate the whole view with a
 * single call.
 *
 * A room's edges come from EXACTLY ONE of two sources, never both and never blended:
 *   - the cloud's seat links, when the room has any; otherwise
 *   - the online machine report (`GET /api/v2/openrig/machines`, the `edges` array the
 *     per-PC bridge sends), because the cloud refuses allow=true links on omp seats, so a
 *     running rig's real edges only exist in that report.
 * `edgeSource` records which one was used, so the page can say it rather than imply it.
 * Cloud links WIN when both exist: the report is read but its edges are not added to them.
 *
 * @module hooks/useTopology
 * @version 2.0.0
 */

import { useQuery } from '@tanstack/react-query';
import { seatApi } from '../services/seatApi';
import type { MachineEdge, MachineStatus, Room, Seat, SeatLink, SeatLinkKind } from '../types/seatTypes';

/** Which source a room's drawn edges came from. */
export type RoomEdgeSource = 'cloud' | 'report' | 'none';

/** One drawable edge. Both sources normalize to this, so the graph has one path. */
export interface TopologyEdge {
  /** Stable React key, unique within its room. */
  id: string;
  from_seat_id: string;
  to_seat_id: string;
  kind: SeatLinkKind;
  /**
   * The cloud link's `allow` flag, or `null` when the source is the machine report - which carries
   * no allow flag at all. `null` is NOT `false`: a report edge is a running edge, not a denial.
   */
  allow: boolean | null;
}

/** One room and the nodes and edges that belong to it. */
export interface RoomTopology {
  room: Room;
  seats: Seat[];
  /** The edges to draw, from ONE source only; see `edgeSource`. */
  edges: TopologyEdge[];
  edgeSource: RoomEdgeSource;
}

export const topologyKeys = {
  /** The whole topology; `useRealtimeSync` invalidates this on every seat event. */
  all: ['seatTopology'] as const,
};

/**
 * Edges from ONLINE machines only: an offline machine's last report is its past, not the rig's
 * running shape. `edges` is absent on a machine whose report predates the server half.
 */
function reportedEdges(machines: MachineStatus[]): { edges: MachineEdge[]; anyOnline: boolean } {
  const online = machines.filter((machine) => machine.online);
  return {
    edges: online.flatMap((machine) => machine.edges ?? []),
    anyOnline: online.length > 0,
  };
}

function cloudEdges(links: SeatLink[]): TopologyEdge[] {
  return links.map((link) => ({
    id: link.id,
    from_seat_id: link.from_seat_id,
    to_seat_id: link.to_seat_id,
    kind: link.kind,
    allow: link.allow,
  }));
}

/**
 * The selection rule, in one place: cloud links when the room has any, else the report's edges for
 * that room. The two sets are never concatenated - a room drawn from the report has NO cloud edges
 * in its list and vice versa.
 */
function roomEdges(
  room: Room,
  seats: Seat[],
  cloudLinks: SeatLink[],
  reported: MachineEdge[],
  anyOnline: boolean
): RoomTopology {
  if (cloudLinks.length > 0) {
    return { room, seats, edges: cloudEdges(cloudLinks), edgeSource: 'cloud' };
  }

  const idByKey = new Map(seats.map((seat) => [seat.seat_key, seat.id]));
  const edges = reported.flatMap((edge, index) => {
    if (edge.room !== room.slug) return [];
    const from = idByKey.get(edge.from);
    const to = idByKey.get(edge.to);
    // An edge whose endpoints are not both seats of THIS room cannot be drawn on it. It is dropped
    // rather than moved to another room, and the count the page shows is what was drawn.
    if (!from || !to) return [];
    return [
      {
        id: `report:${room.slug}:${edge.from}:${edge.to}:${edge.kind}:${index}`,
        from_seat_id: from,
        to_seat_id: to,
        kind: edge.kind,
        allow: null,
      },
    ];
  });

  // `report` is the source whenever a machine is reporting at all, even if it lists no edge for
  // this room - the alternative would be to call a reported-but-crossed room "nothing", which
  // overstates the absence. `none` means precisely: no cloud links and no machine reporting.
  return { room, seats, edges, edgeSource: anyOnline ? 'report' : 'none' };
}

async function fetchTopology(): Promise<RoomTopology[]> {
  const [roomsResponse, machinesResponse] = await Promise.all([
    seatApi.listRooms(),
    seatApi.fetchMachines(),
  ]);
  const rooms = roomsResponse.rooms ?? [];
  const { edges: reported, anyOnline } = reportedEdges(machinesResponse.machines ?? []);

  return Promise.all(
    rooms.map(async (room) => {
      const seatsResponse = await seatApi.listSeats(room.slug);
      const seats = seatsResponse.seats ?? [];
      const linkResponses = await Promise.all(
        seats.map((seat) => seatApi.listLinks(room.slug, seat.seat_key))
      );
      const cloudLinks = linkResponses.flatMap((response) => response.links ?? []);
      return roomEdges(room, seats, cloudLinks, reported, anyOnline);
    })
  );
}

/** Every room with its seats and its edges; one query for the whole graph. */
export function useTopology() {
  const query = useQuery({
    queryKey: topologyKeys.all,
    queryFn: fetchTopology,
  });
  return {
    rooms: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
