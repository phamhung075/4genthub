export { useTheme } from './useTheme';
export { useTaskFilters } from './useTaskFilters';
export { useTaskGrouping } from './useTaskGrouping';

// Agent Management Hooks (User-Specific Agent System)
export {
  useAgentTemplates,
  useUserAgentInstances,
  useAgentSharing,
  useAgentMarketplace,
  useAgentAnalytics,
} from './useAgentManagement';

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
