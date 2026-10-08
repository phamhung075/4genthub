/**
 * Seat API - Company-workplace seats, modules and overlays.
 *
 * Every call goes through the shared authenticated V2 client (`apiRequest`);
 * this module only encodes the /api/v2/openrig routes.
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
} from '../types/seatTypes';

const OPENRIG = '/api/v2/openrig';

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
      return `${OPENRIG}/overlay`;
    case 'room':
      return `${OPENRIG}/rooms/${segment(room)}/overlay`;
    case 'seat':
      return `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/overlay`;
  }
}

export const seatApi = {
  // Rooms
  listRooms: () => apiRequest<RoomsResponse>(`${OPENRIG}/rooms`),

  createRoom: (data: CreateRoomRequest) =>
    apiRequest<RoomResponse>(`${OPENRIG}/rooms`, jsonBody(data)),

  deleteRoom: (room: string) =>
    apiRequest<DeletedResponse>(`${OPENRIG}/rooms/${segment(room)}`, { method: 'DELETE' }),

  // Seat types and modules
  listSeatTypes: () => apiRequest<SeatTypesResponse>(`${OPENRIG}/seat-types`),

  createSeatTypeVersion: (slug: string, data: CreateSeatTypeVersionRequest) =>
    apiRequest<SeatTypeVersionResponse>(
      `${OPENRIG}/seat-types/${segment(slug)}/versions`,
      jsonBody(data)
    ),

  listModules: () => apiRequest<ModulesResponse>(`${OPENRIG}/modules`),

  getModuleVersion: (slug: string, version: string) =>
    apiRequest<ModuleVersionResponse>(
      `${OPENRIG}/modules/${segment(slug)}/versions/${segment(version)}`
    ),

  putModuleVersion: (slug: string, version: string, data: PutModuleVersionRequest) =>
    apiRequest<PutModuleVersionResponse>(
      `${OPENRIG}/modules/${segment(slug)}/versions/${segment(version)}`,
      jsonPut(data)
    ),

  // Seats
  listSeats: (room: string) =>
    apiRequest<SeatsResponse>(`${OPENRIG}/rooms/${segment(room)}/seats`),

  createSeat: (room: string, data: CreateSeatRequest) =>
    apiRequest<SeatResponse>(`${OPENRIG}/rooms/${segment(room)}/seats`, jsonBody(data)),

  removeSeat: (room: string, seat: string) =>
    apiRequest<DeletedResponse>(
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}`,
      { method: 'DELETE' }
    ),

  updateSeatOccupant: (room: string, seat: string, data: OccupantUpdate) =>
    apiRequest<SeatResponse>(
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/occupant`,
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
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/links`
    ),

  putLink: (room: string, seat: string, data: SeatLinkRequest) =>
    apiRequest<SeatLinkResponse>(
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/links`,
      jsonPut(data)
    ),

  putPermissionPolicy: (room: string, seat: string, permissionPolicy: SeatPermissionPolicy) =>
    apiRequest<SeatResponse>(
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/permission-policy`,
      jsonPut({ permission_policy: permissionPolicy })
    ),

  deleteLink: (room: string, seat: string, to: string, kind: SeatLinkKind) =>
    apiRequest<DeletedResponse>(
      `${OPENRIG}/rooms/${segment(room)}/seats/${segment(seat)}/links/${segment(to)}/${segment(kind)}`,
      { method: 'DELETE' }
    ),

  // Messages. The seat key is the whole path: this route is not room-scoped, unlike the rest.
  sendSeatMessage: (seat: string, data: SeatMessageRequest) =>
    apiRequest<SeatMessageResponse>(`${OPENRIG}/seats/${segment(seat)}/messages`, jsonBody(data)),

  // Bridge machines
  fetchMachines: () => apiRequest<MachinesResponse>(`${OPENRIG}/machines`),

  // Settings
  getSettings: () => apiRequest<SeatSettingsResponse>(`${OPENRIG}/settings`),

  putSettings: (followLatest: boolean) =>
    apiRequest<SeatSettingsResponse>(`${OPENRIG}/settings`, jsonPut({ follow_latest: followLatest })),

  // Resolved preview
  getResolvedSeat: (room: string, seat: string) =>
    apiRequest<ResolvedSeatResponse>(
      `${OPENRIG}/seats/${segment(room)}/${segment(seat)}`
    ),
};
