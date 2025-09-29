// LazySubtaskList - Barrel exports for clean imports
// Refactored modular structure following SOLID principles

// Main component export
export { default } from "./LazySubtaskListRefactored";
export { LazySubtaskListRefactored } from "./LazySubtaskListRefactored";

// Hook exports (for testing and reuse)
export { useSubtaskData } from "./hooks/useSubtaskData";
export { useSubtaskFilters } from "./hooks/useSubtaskFilters";
export { useSubtaskWebSocket } from "./hooks/useSubtaskWebSocket";
export { useSubtaskExpansion } from "./hooks/useSubtaskExpansion";
export { useSubtaskDialogs } from "./hooks/useSubtaskDialogs";

// Component exports (for reuse)
export { SubtaskListHeader } from "./components/SubtaskListHeader";
export { SubtaskListContent } from "./components/SubtaskListContent";
export { SubtaskActions } from "./components/SubtaskActions";
export { SubtaskDialogs } from "./components/SubtaskDialogs";

// Type exports
export type {
  LazySubtaskListProps,
  BadgeVariant,
  AnimationTriggers,
  RowAnimationCallbacks,
  DeleteDialogState,
  ActiveDialogState,
  DetailsDialogState,
  SubtaskDataState,
  SubtaskExpansionState,
  DialogState,
  SubtaskChangePayload,
  SubtaskFilterOptions,
  SubtaskListConfig,
  UseSubtaskDataReturn,
  UseSubtaskFiltersReturn,
  UseSubtaskWebSocketReturn,
  UseSubtaskExpansionReturn,
  UseSubtaskDialogsReturn
} from "../../types/subtaskTypes";

// Utility exports
export {
  subtaskToSummary,
  subtasksToSummaries,
  isValidSubtaskId,
  filterSubtasks,
  calculateProgressSummary,
  sortSubtasks,
  detectSubtaskChanges,
  generateSubtaskDialogUrl,
  generateBranchUrl,
  debounce,
  logSubtaskError,
  createEmptySubtaskDataState
} from "./utils/subtaskHelpers";

// Constants exports
export {
  STATUS_COLOR_MAP,
  PRIORITY_COLOR_MAP,
  ANIMATION_CONFIG,
  LOADING_CONFIG,
  DIALOG_CONFIG
} from "./constants/subtaskConstants";