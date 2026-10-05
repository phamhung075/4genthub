/**
 * Topology Hooks - the whole workspace as rooms, seats and links in one query.
 *
 * F6 reads three existing routes and folds them into one shape: rooms
 * (`GET /api/v2/openrig/rooms`), seats per room (`/rooms/{room}/seats`) and
 * links per seat (`/rooms/{room}/seats/{seat}/links`, which returns the links
 * FROM that seat, so one call per seat covers every edge). It is one React
 * Query key so the realtime seat handler can invalidate the whole view with a
 * single call.
 *
 * @module hooks/useTopology
 * @version 1.0.0
 */

import { useQuery } from '@tanstack/react-query';
import { seatApi } from '../services/seatApi';
import type { Room, Seat, SeatLink } from '../types/seatTypes';

/** One room and the nodes and edges that belong to it. */
export interface RoomTopology {
  room: Room;
  seats: Seat[];
  links: SeatLink[];
}

export const topologyKeys = {
  /** The whole topology; `useRealtimeSync` invalidates this on every seat event. */
  all: ['seatTopology'] as const,
};

async function fetchTopology(): Promise<RoomTopology[]> {
  const roomsResponse = await seatApi.listRooms();
  const rooms = roomsResponse.rooms ?? [];

  return Promise.all(
    rooms.map(async (room) => {
      const seatsResponse = await seatApi.listSeats(room.slug);
      const seats = seatsResponse.seats ?? [];
      const linkResponses = await Promise.all(
        seats.map((seat) => seatApi.listLinks(room.slug, seat.seat_key))
      );
      return { room, seats, links: linkResponses.flatMap((response) => response.links ?? []) };
    })
  );
}

/** Every room with its seats and links; one query for the whole graph. */
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
