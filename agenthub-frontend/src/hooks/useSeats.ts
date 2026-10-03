/**
 * Seat Hooks - React Query bindings for the company-workplace seat API.
 *
 * Queries are tenant-scoped by the shared client; mutations only invalidate
 * the affected query keys (no optimistic cache writes).
 *
 * @module hooks/useSeats
 * @version 1.0.0
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { seatApi } from '../services/seatApi';
import { useSuccessToast } from '../components/ui/toast';
import type {
  CreateSeatTypeVersionRequest,
  ModuleSummary,
  CreateRoomRequest,
  CreateSeatRequest,
  MachineStatus,
  OccupantUpdate,
  PutModuleVersionRequest,
  SeatLinkKind,
  SeatLinkRequest,
  SeatOverlay,
  SeatOverlayOp,
  SeatOverlayScope,
  SeatOverlays,
  SeatSettings,
  SeatType,
} from '../types/seatTypes';

export type { SeatOverlays };

export const seatKeys = {
  rooms: ['seatRooms'] as const,
  seatTypes: ['seatTypes'] as const,
  settings: ['seatSettings'] as const,
  machines: ['seatMachines'] as const,
  seats: (room: string) => ['seatSeats', room] as const,
  overlays: (room: string, seat: string) => ['seatOverlays', room, seat] as const,
  links: (room: string, seat: string) => ['seatLinks', room, seat] as const,
  resolved: (room: string, seat: string) => ['seatResolved', room, seat] as const,
  modules: ['seatModules'] as const,
  module: (slug: string, version: string) => ['seatModule', slug, version] as const,
};

const emptyOverlay = (scope: SeatOverlayScope): SeatOverlay => ({ scope, ops: [] });

// ---------------------------------------------------------------------------
// Rooms
// ---------------------------------------------------------------------------

export function useRooms() {
  const query = useQuery({
    queryKey: seatKeys.rooms,
    queryFn: async () => {
      const response = await seatApi.listRooms();
      return response.rooms ?? [];
    },
  });
  return { rooms: query.data ?? [], isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

export function useCreateRoom() {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (data: CreateRoomRequest) => seatApi.createRoom(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.rooms });
      showSuccess(`Room "${response.room.name}" created`);
    },
  });
}

export function useDeleteRoom() {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (room: string) => seatApi.deleteRoom(room),
    onSuccess: (_response, room) => {
      queryClient.removeQueries({ queryKey: seatKeys.seats(room) });
      queryClient.invalidateQueries({ queryKey: seatKeys.rooms });
      showSuccess(`Room "${room}" deleted`);
    },
  });
}

// ---------------------------------------------------------------------------
// Seat types
// ---------------------------------------------------------------------------

export function useSeatTypes() {
  const query = useQuery({
    queryKey: seatKeys.seatTypes,
    queryFn: async (): Promise<SeatType[]> => {
      const response = await seatApi.listSeatTypes();
      return response.seat_types ?? [];
    },
  });
  return {
    seatTypes: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useCreateSeatTypeVersion(slug: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (data: CreateSeatTypeVersionRequest) => seatApi.createSeatTypeVersion(slug, data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.seatTypes });
      showSuccess(`Seat type ${slug} version ${response.seat_type_version.version} created`);
    },
  });
}

export function useModuleVersion(slug: string | null, version: string | null, enabled = true) {
  const query = useQuery({
    queryKey: seatKeys.module(slug ?? '', version ?? ''),
    queryFn: async () => {
      const response = await seatApi.getModuleVersion(slug as string, version as string);
      return response.module;
    },
    enabled: enabled && !!slug && !!version && version !== 'latest',
  });
  return { module: query.data ?? null, isLoading: query.isLoading, error: query.error };
}

export function useModules() {
  const query = useQuery({
    queryKey: seatKeys.modules,
    queryFn: async (): Promise<ModuleSummary[]> => {
      const response = await seatApi.listModules();
      return response.modules ?? [];
    },
  });
  return { modules: query.data ?? [], isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

export function usePublishModuleVersion() {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: ({ slug, version, ...data }: PutModuleVersionRequest & { slug: string; version: string }) =>
      seatApi.putModuleVersion(slug, version, data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.modules });
      showSuccess(`Module ${response.module.slug}@${response.module.version} published`);
    },
  });
}

// ---------------------------------------------------------------------------
// Seats
// ---------------------------------------------------------------------------

export function useSeats(room: string) {
  const query = useQuery({
    queryKey: seatKeys.seats(room),
    queryFn: async () => {
      const response = await seatApi.listSeats(room);
      return response.seats ?? [];
    },
    enabled: !!room,
  });
  return { seats: query.data ?? [], isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

export function useCreateSeat(room: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (data: CreateSeatRequest) => seatApi.createSeat(room, data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.seats(room) });
      showSuccess(`Seat "${response.seat.seat_key}" added`);
    },
  });
}

export function useRemoveSeat(room: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (seat: string) => seatApi.removeSeat(room, seat),
    onSuccess: (_response, seat) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.seats(room) });
      showSuccess(`Seat "${seat}" removed`);
    },
  });
}

export function useUpdateSeatOccupant(room: string, seat: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (data: OccupantUpdate) => seatApi.updateSeatOccupant(room, seat, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: seatKeys.seats(room) });
      queryClient.invalidateQueries({ queryKey: seatKeys.resolved(room, seat) });
      showSuccess(`Seat "${seat}" LLM saved`);
    },
  });
}

// ---------------------------------------------------------------------------
// Bridge machines
// ---------------------------------------------------------------------------

const MACHINES_REFETCH_MS = 15000;

export function useMachines() {
  const query = useQuery({
    queryKey: seatKeys.machines,
    queryFn: async (): Promise<MachineStatus[]> => {
      const response = await seatApi.fetchMachines();
      return response.machines ?? [];
    },
    refetchInterval: MACHINES_REFETCH_MS,
  });
  return { machines: query.data ?? [], isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export function useSeatSettings() {
  const query = useQuery({
    queryKey: seatKeys.settings,
    queryFn: async (): Promise<SeatSettings> => {
      const response = await seatApi.getSettings();
      return response.settings;
    },
  });
  return { settings: query.data ?? null, isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

export function useUpdateSeatSettings() {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (followLatest: boolean) => seatApi.putSettings(followLatest),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.settings });
      showSuccess(
        response.settings.follow_latest
          ? 'Company now follows the latest seat versions'
          : 'Company now pins seat versions'
      );
    },
  });
}

// ---------------------------------------------------------------------------
// Overlays
// ---------------------------------------------------------------------------

export function useSeatOverlays(room: string, seat: string) {
  const query = useQuery({
    queryKey: seatKeys.overlays(room, seat),
    queryFn: async (): Promise<SeatOverlays> => {
      const [company, roomOverlay, seatOverlay] = await Promise.all([
        seatApi.getOverlay('company', room, seat),
        seatApi.getOverlay('room', room, seat),
        seatApi.getOverlay('seat', room, seat),
      ]);
      return {
        company: company.overlay ?? emptyOverlay('company'),
        room: roomOverlay.overlay ?? emptyOverlay('room'),
        seat: seatOverlay.overlay ?? emptyOverlay('seat'),
      };
    },
    enabled: !!room && !!seat,
  });
  const overlays = query.data;
  return {
    overlays,
    companyOverlay: overlays?.company ?? emptyOverlay('company'),
    roomOverlay: overlays?.room ?? emptyOverlay('room'),
    seatOverlay: overlays?.seat ?? emptyOverlay('seat'),
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useUpdateOverlay(room: string, seat: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: ({ scope, ops }: { scope: SeatOverlayScope; ops: SeatOverlayOp[] }) =>
      seatApi.putOverlay(scope, { ops }, room, seat),
    onSuccess: (_response, variables) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.overlays(room, seat) });
      queryClient.invalidateQueries({ queryKey: seatKeys.resolved(room, seat) });
      showSuccess(`${variables.scope} overlay saved`);
    },
  });
}

// ---------------------------------------------------------------------------
// Links
// ---------------------------------------------------------------------------

export function useSeatLinks(room: string, seat: string) {
  const query = useQuery({
    queryKey: seatKeys.links(room, seat),
    queryFn: async () => {
      const response = await seatApi.listLinks(room, seat);
      return response.links ?? [];
    },
    enabled: !!room && !!seat,
  });
  return { links: query.data ?? [], isLoading: query.isLoading, error: query.error, refetch: query.refetch };
}

export function useUpsertSeatLink(room: string, seat: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: (data: SeatLinkRequest) => seatApi.putLink(room, seat, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: seatKeys.links(room, seat) });
      showSuccess('Seat link saved');
    },
  });
}

export function useDeleteSeatLink(room: string, seat: string) {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  return useMutation({
    mutationFn: ({ to, kind }: { to: string; kind: SeatLinkKind }) =>
      seatApi.deleteLink(room, seat, to, kind),
    onSuccess: (_response, { to, kind }) => {
      queryClient.invalidateQueries({ queryKey: seatKeys.links(room, seat) });
      showSuccess(`Link ${kind} to "${to}" deleted`);
    },
  });
}

// ---------------------------------------------------------------------------
// Resolved preview
// ---------------------------------------------------------------------------

export function useResolvedSeat(room: string, seat: string) {
  const query = useQuery({
    queryKey: seatKeys.resolved(room, seat),
    queryFn: async () => {
      const response = await seatApi.getResolvedSeat(room, seat);
      return response.resolved_seat;
    },
    enabled: !!room && !!seat,
  });
  return {
    resolvedSeat: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
