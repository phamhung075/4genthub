/**
 * Seat API - Company-workplace seats, modules and overlays.
 *
 * Every call goes through the shared authenticated V2 client (`apiRequest`);
 * this module only encodes the /api/v2 routes.
 *
 * @module services/seatApi
 * @version 1.0.0
 */

import { apiRequest } from './apiV2';
import type {
  CreateSeatTypeVersionRequest,
  ModulesResponse,
  SeatTypeVersionResponse,
  CreateRoomRequest,
  CreateSeatRequest,
  MachinesResponse,
  OccupantUpdate,
  ModuleVersionResponse,
  PutModuleVersionRequest,
  PutModuleVersionResponse,
  PutSeatOverlayRequest,
  DeletedResponse,
  ResolvedSeatResponse,
  RoomResponse,
  RoomsResponse,
  SeatLinksResponse,
  SeatLinkKind,
  SeatPermissionPolicy,
  SeatLinkRequest,
  SeatLinkResponse,
  SeatMessageRequest,
  SeatMessageResponse,
  SeatOverlayResponse,
  SeatOverlayScope,
  SeatResponse,
  SeatSettingsResponse,
  SeatTypesResponse,
  SeatsResponse,
  TeamsResponse,
} from '../types/seatTypes';

const API_V2 = '/api/v2';

const segment = (value: string) => encodeURIComponent(value);

const jsonBody = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

const jsonPut = (body: unknown): RequestInit => ({
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

// Company overlay has no room or seat, a room overlay only a room, a seat
// overlay only a room and a seat.
function overlayPath(scope: SeatOverlayScope, room: string, seat: string): string {
  switch (scope) {
    case 'company':
      return `${API_V2}/overlay`;
    case 'room':
      return `${API_V2}/rooms/${segment(room)}/overlay`;
    case 'seat':
      return `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/overlay`;
  }
}

export const seatApi = {
  // Rooms
  listRooms: () => apiRequest<RoomsResponse>(`${API_V2}/rooms`),

  createRoom: (data: CreateRoomRequest) =>
    apiRequest<RoomResponse>(`${API_V2}/rooms`, jsonBody(data)),

  deleteRoom: (room: string) =>
    apiRequest<DeletedResponse>(`${API_V2}/rooms/${segment(room)}`, { method: 'DELETE' }),

  /**
   * Share one room with one team, or make it private again with an empty team.
   *
   * OWNER-ONLY ON THE WIRE: the handler resolves the room through `GetRoomBySlug(userID, slug)`, which
   * returns the caller's own room only, so a viewer's call is a 404 in the server's own words, and a
   * team slug outside the caller's memberships is a 404 too. The caller must hold the room body's
   * `role: 'owner'` before this is offered - the page does not probe the refusal.
   */
  setRoomTeam: (room: string, team: string) =>
    apiRequest<RoomResponse>(`${API_V2}/rooms/${segment(room)}/team`, jsonPut({ team })),

  /** The teams the caller belongs to; the picker's options, and the only slugs the route accepts. */
  listTeams: () => apiRequest<TeamsResponse>(`${API_V2}/teams`),

  // Seat types and modules
  listSeatTypes: () => apiRequest<SeatTypesResponse>(`${API_V2}/seat-types`),

  createSeatTypeVersion: (slug: string, data: CreateSeatTypeVersionRequest) =>
    apiRequest<SeatTypeVersionResponse>(
      `${API_V2}/seat-types/${segment(slug)}/versions`,
      jsonBody(data)
    ),

  listModules: () => apiRequest<ModulesResponse>(`${API_V2}/modules`),

  getModuleVersion: (slug: string, version: string) =>
    apiRequest<ModuleVersionResponse>(
      `${API_V2}/modules/${segment(slug)}/versions/${segment(version)}`
    ),

  putModuleVersion: (slug: string, version: string, data: PutModuleVersionRequest) =>
    apiRequest<PutModuleVersionResponse>(
      `${API_V2}/modules/${segment(slug)}/versions/${segment(version)}`,
      jsonPut(data)
    ),

  // Seats
  listSeats: (room: string) =>
    apiRequest<SeatsResponse>(`${API_V2}/rooms/${segment(room)}/seats`),

  createSeat: (room: string, data: CreateSeatRequest) =>
    apiRequest<SeatResponse>(`${API_V2}/rooms/${segment(room)}/seats`, jsonBody(data)),

  removeSeat: (room: string, seat: string) =>
    apiRequest<DeletedResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}`,
      { method: 'DELETE' }
    ),

  updateSeatOccupant: (room: string, seat: string, data: OccupantUpdate) =>
    apiRequest<SeatResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/occupant`,
      jsonPut(data)
    ),

  // Overlays
  getOverlay: (scope: SeatOverlayScope, room: string, seat: string) =>
    apiRequest<SeatOverlayResponse>(overlayPath(scope, room, seat)),

  putOverlay: (
    scope: SeatOverlayScope,
    data: PutSeatOverlayRequest,
    room: string,
    seat: string
  ) => apiRequest<SeatOverlayResponse>(overlayPath(scope, room, seat), jsonPut(data)),

  // Links
  listLinks: (room: string, seat: string) =>
    apiRequest<SeatLinksResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/links`
    ),

  putLink: (room: string, seat: string, data: SeatLinkRequest) =>
    apiRequest<SeatLinkResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/links`,
      jsonPut(data)
    ),

  putPermissionPolicy: (room: string, seat: string, permissionPolicy: SeatPermissionPolicy) =>
    apiRequest<SeatResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/permission-policy`,
      jsonPut({ permission_policy: permissionPolicy })
    ),

  deleteLink: (room: string, seat: string, to: string, kind: SeatLinkKind) =>
    apiRequest<DeletedResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/links/${segment(to)}/${segment(kind)}`,
      { method: 'DELETE' }
    ),

  // Messages. Room-scoped like every other seat route: a seat is unique per (room_id, seat_key),
  // so the key alone names a seat only by guessing its room.
  sendSeatMessage: (room: string, seat: string, data: SeatMessageRequest) =>
    apiRequest<SeatMessageResponse>(
      `${API_V2}/rooms/${segment(room)}/seats/${segment(seat)}/messages`,
      jsonBody(data)
    ),

  // Bridge machines
  fetchMachines: () => apiRequest<MachinesResponse>(`${API_V2}/machines`),

  // Settings
  getSettings: () => apiRequest<SeatSettingsResponse>(`${API_V2}/settings`),

  putSettings: (followLatest: boolean) =>
    apiRequest<SeatSettingsResponse>(`${API_V2}/settings`, jsonPut({ follow_latest: followLatest })),

  // Resolved preview
  getResolvedSeat: (room: string, seat: string) =>
    apiRequest<ResolvedSeatResponse>(
      `${API_V2}/seats/${segment(room)}/${segment(seat)}`
    ),
};
