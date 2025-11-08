// ============================================
// Subtask Types - Consolidated from LazySubtaskList
// ============================================

import type { SubtaskSummary } from "./taskTypes";
import type { AnimationCallbacks, SubtaskAnimationState } from "./animationTypes";

/**
 * Main props for LazySubtaskList component
 */
export interface LazySubtaskListProps {
  projectId: string;
  taskTreeId: string;
  parentTaskId: string;
}

/**
 * Badge variant type (from UI library)
 */
export type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

/**
 * Animation trigger state
 */
export interface AnimationTriggers {
  created: Set<string>;
  updated: Set<string>;
  deleted: Set<string>;
}

/**
 * Row animation callback functions
 */
export interface RowAnimationCallbacks {
  playCreateAnimation: () => void;
  playDeleteAnimation: () => void;
  playUpdateAnimation: () => void;
}

/**
 * Delete dialog state
 */
export interface DeleteDialogState {
  open: boolean;
  subtaskId: string | null;
}

/**
 * Active dialog state with union type for type safety
 */
export interface ActiveDialogState {
  type: 'details' | 'edit' | 'complete' | null;
  subtaskId?: string;
  subtask?: any; // Subtask from API
}

/**
 * Details dialog state
 */
export interface DetailsDialogState {
  open: boolean;
  subtask: any | null; // Subtask from API
}

/**
 * Subtask data management state
 */
export interface SubtaskDataState {
  subtaskSummaries: SubtaskSummary[];
  fullSubtasks: Map<string, any>; // Map of Subtask from API
  loading: boolean;
  error: string | null;
  loadingSubtasks: Set<string>;
  hasLoaded: boolean;
  subscriptionEnabled: boolean;
}

/**
 * Subtask expansion state
 */
export interface SubtaskExpansionState {
  previousSubtaskIds: Set<string>;
  animationTriggers: AnimationTriggers;
  isOpeningDialog: boolean;
  editingSubtask: any | null; // Subtask from API
  showDetails: string | null;
}

/**
 * Dialog management state
 */
export interface DialogState {
  deleteDialog: DeleteDialogState;
  activeDialog: ActiveDialogState;
  detailsDialog: DetailsDialogState;
  selectedAgentForInfo: string | null;
  agentInfoDialogOpen: boolean;
  createSubtaskDialogOpen: boolean;
}

/**
 * WebSocket change subscription payload
 */
export interface SubtaskChangePayload {
  type: 'created' | 'updated' | 'deleted';
  subtask: any | SubtaskSummary; // Subtask from API or summary
  timestamp: string;
}

/**
 * Subtask filter options
 */
export interface SubtaskFilterOptions {
  status?: string[];
  priority?: string[];
  assignees?: string[];
  searchTerm?: string;
}

/**
 * Subtask list configuration
 */
export interface SubtaskListConfig {
  enableAnimations: boolean;
  enableRealTimeUpdates: boolean;
  showProgressPercentage: boolean;
  showAssigneeCount: boolean;
  defaultSortField: 'created_at' | 'updated_at' | 'priority' | 'status';
  defaultSortDirection: 'asc' | 'desc';
}

/**
 * Hook return types for custom hooks
 */
export interface UseSubtaskDataReturn extends SubtaskDataState {
  loadSubtaskSummaries: () => Promise<void>;
  loadFullSubtasksFallback: () => Promise<Map<string, any>>; // Map of Subtask from API
  loadSubtaskById: (subtaskId: string) => Promise<any | null>; // Load individual subtask
  handleSubtaskCreated: (newSubtask: any) => void; // Subtask from API
  refreshData: () => Promise<void>;
}

export interface UseSubtaskFiltersReturn {
  filteredSubtasks: SubtaskSummary[];
  filterOptions: SubtaskFilterOptions;
  setFilterOptions: (options: SubtaskFilterOptions) => void;
  clearFilters: () => void;
}

export interface UseSubtaskWebSocketReturn {
  isConnected: boolean;
  reconnect: () => void;
  disconnect: () => void;
}

export interface UseSubtaskExpansionReturn extends SubtaskExpansionState {
  registerRowCallbacks: (subtaskId: string, callbacks: RowAnimationCallbacks) => void;
  unregisterRowCallbacks: (subtaskId: string) => void;
  triggerAnimation: (subtaskId: string, type: 'create' | 'update' | 'delete') => void;
  setShowDetails: (subtaskId: string | null) => void;
  setEditingSubtask: (subtask: any | null) => void; // Subtask from API
  setIsOpeningDialog: (opening: boolean) => void;
}

export interface UseSubtaskDialogsReturn extends DialogState {
  handleSubtaskDialogClose: () => void;
  handleAgentInfoClick: (agentName: string) => void;
  handleOpenCreateSubtask: () => void;
  openDetailsDialog: (subtask: any) => void; // Subtask from API
  openEditDialog: (subtask: any) => void; // Subtask from API
  openCompleteDialog: (subtask: any) => void; // Subtask from API
  openDeleteDialog: (subtaskId: string) => void;
  closeDeleteDialog: () => void;
  closeDetailsDialog: () => void;
  closeAgentInfoDialog: () => void;
  closeCreateSubtaskDialog: () => void;
  closeAllDialogs: () => void;
  handleDialogAction: (action: 'details' | 'edit' | 'complete', subtaskId: string, subtask?: any) => void;
  hasOpenDialog: boolean;
  isClosingRef: React.MutableRefObject<boolean>; // Ref to prevent race condition on close
}

// ============================================
// SubtaskRow Types
// ============================================

export interface SubtaskRowProps {
  summary: SubtaskSummary;
  fullSubtask: any | null; // Full Subtask from API
  isLoading: boolean;
  showDetails: boolean;
  parentTaskId: string;
  onSubtaskAction: (action: 'details' | 'edit' | 'complete', subtaskId: string) => void;
  onAgentInfoClick: (agentName: string) => void;
  onDeleteSubtask: (subtaskId: string) => void;
  onRegisterCallbacks?: (subtaskId: string, callbacks: AnimationCallbacks) => void;
  onUnregisterCallbacks?: (subtaskId: string) => void;
}

/**
 * Animation callback types
 * @see {import('./animationTypes').AnimationCallbacks}
 * @see {import('./animationTypes').SubtaskAnimationState}
 * Note: Import from animationTypes - duplicates removed to avoid barrel export conflicts
 */

export interface SubtaskRowActionsProps {
  subtaskId: string;
  onView: () => void;
  onEdit: () => void;
  onComplete: () => void;
  onDelete: () => void;
}

export interface SubtaskRowBadgesProps {
  status: string;
  priority: string;
  progressPercentage?: number;
}

export interface SubtaskRowAssigneesProps {
  assignees?: string[];
  assigneesCount: number;
  onAgentInfoClick: (agentName: string) => void;
}