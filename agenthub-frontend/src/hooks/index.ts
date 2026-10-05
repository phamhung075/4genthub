export { useTheme } from './useTheme';
export { useTaskFilters } from './useTaskFilters';
export { useTaskGrouping } from './useTaskGrouping';

// Seat Hooks (Company-workplace model)
export {
  seatKeys,
  useRooms,
  useCreateRoom,
  useSeatTypes,
  useModuleVersion,
  useSeats,
  useCreateSeat,
  useRemoveSeat,
  useSeatSettings,
  useUpdateSeatSettings,
  useSeatOverlays,
  useUpdateOverlay,
  useSeatLinks,
  useUpsertSeatLink,
  useResolvedSeat,
} from './useSeats';
export type { SeatOverlays } from './useSeats';
