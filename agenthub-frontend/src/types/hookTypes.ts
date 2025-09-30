/**
 * React Hook Types
 * Consolidated types for custom React hooks
 */

import type { BranchSummary, ProjectSummary } from './api.types';
import type { TokenPermissions } from './authTypes';
import type { TaskPriority, TaskStatus, TaskSummary } from './taskTypes';

// =============================================================================
// Task Grouping Hook Types
// =============================================================================

export type GroupBy = 'none' | 'status' | 'priority' | 'assignee';
export type SortBy = 'title' | 'status' | 'priority' | 'created_at' | 'updated_at';
export type SortOrder = 'asc' | 'desc';

export interface TaskGroup {
  groupKey: string;
  groupLabel: string;
  tasks: TaskSummary[];
  count: number;
}

export interface TaskSorting {
  sortBy: SortBy;
  sortOrder: SortOrder;
}

export interface UseTaskGroupingReturn {
  groupBy: GroupBy;
  sorting: TaskSorting;
  setGroupBy: (groupBy: GroupBy) => void;
  setSorting: (sorting: Partial<TaskSorting>) => void;
  sortTasks: (tasks: TaskSummary[]) => TaskSummary[];
  groupTasks: (tasks: TaskSummary[]) => TaskGroup[];
  processedTasks: TaskSummary[] | TaskGroup[];
  isGrouped: boolean;
}

// =============================================================================
// Task Filters Hook Types
// =============================================================================

export interface TaskFilters {
  search: string;
  status: TaskStatus | 'all';
  priority: TaskPriority | 'all';
  assignee: string | 'all';
}

export interface UseTaskFiltersReturn {
  filters: TaskFilters;
  setSearchFilter: (search: string) => void;
  setStatusFilter: (status: TaskStatus | 'all') => void;
  setPriorityFilter: (priority: TaskPriority | 'all') => void;
  setAssigneeFilter: (assignee: string | 'all') => void;
  clearFilters: () => void;
  applyFilters: (tasks: TaskSummary[]) => TaskSummary[];
  filteredTaskCount: number;
}

// =============================================================================
// Branch Summaries Hook Types
// =============================================================================

export interface UseBranchSummariesOptions {
  projectIds?: string[];
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
}

export interface UseBranchSummariesResult {
  summaries: BranchSummary[];
  projects: ProjectSummary[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  forceRefresh: () => Promise<void>;
  refreshing: boolean;
}

// =============================================================================
// Permissions Hook Types
// =============================================================================

export interface UsePermissionsReturn {
  permissions: TokenPermissions;
  hasPermission: (permission: keyof TokenPermissions) => boolean;
  hasFullCrud: boolean;
  canAccessResource: (resource: string) => boolean;
  allowedResources: string[];
  userRoles: string[];
  isLoading: boolean;
  error: string | null;
  refreshPermissions: () => void;
}

// =============================================================================
// Task Data Hook Types
// =============================================================================

/**
 * Options for useTaskData hook
 */
export interface UseTaskDataOptions {
  taskTreeId: string;
  onTasksChanged?: () => void;
}

/**
 * Return type for useTaskData hook
 * Manages task summaries and full task data with loading states
 */
export interface UseTaskDataReturn {
  // State
  taskSummaries: TaskSummary[];
  fullTasks: Map<string, any>; // Using 'any' for Task type to avoid circular dependencies
  totalTasks: number;
  loading: boolean;
  error: string | null;
  loadingTasks: Set<string>;

  // Actions
  loadTaskSummaries: (page?: number) => Promise<void>;
  loadFullTask: (taskId: string) => Promise<any | null>;
  updateTaskFromData: (taskData: any) => void;
  addNewTask: (taskData: any) => void;
  removeTask: (taskId: string) => void;
  setTotalTasks: React.Dispatch<React.SetStateAction<number>>;

  // Utilities
  convertToTaskSummary: (task: any) => TaskSummary;
}

// =============================================================================
// Dialog Manager Hook Types
// =============================================================================

import type { DialogType, ActiveDialog } from './taskTypes';

/**
 * Return type for useDialogManager hook
 * Manages dialog state and operations for task interactions
 */
export interface UseDialogManagerReturn {
  activeDialog: ActiveDialog;
  openDialog: (type: string, taskId?: string, extraData?: any) => void;
  closeDialog: () => void;
  saving: boolean;
  setSaving: (saving: boolean) => void;
  isClosingRef: React.MutableRefObject<boolean>; // Ref to prevent race condition on close
}

// =============================================================================
// Project Hooks Types
// =============================================================================

import type { Project } from '../api';

/**
 * Options for useProjectData hook
 */
export interface UseProjectDataOptions {
  selectedProjectId?: string;
}

/**
 * Return type for useProjectData hook
 * Manages project data, branches, and CRUD operations
 */
export interface UseProjectDataReturn {
  projects: Project[];
  setProjects: React.Dispatch<React.SetStateAction<Project[]>>;
  branchSummaries: Record<string, BranchSummary[]>;
  taskCounts: Record<string, number>;
  loading: boolean;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  loadingBulkSummaries: boolean;
  handleCreateProject: (data: ProjectFormData) => Promise<void>;
  handleUpdateProject: (project: Project, data: ProjectFormData) => Promise<void>;
  handleDeleteProject: (project: Project) => Promise<void>;
  handleCreateBranch: (project: Project, data: ProjectFormData) => Promise<void>;
  handleDeleteBranch: (dialogState: { project: Project; branch: any }, onFadeoutStart: () => void, onFadeoutComplete: () => void) => Promise<void>;
  handleRefresh: () => Promise<void>;
}

/**
 * Options for useProjectAnimations hook
 */
export interface UseProjectAnimationsOptions {
  projects: Project[];
  taskCounts: Record<string, number>;
}

/**
 * Return type for useProjectAnimations hook
 * Manages animation states for project and branch interactions
 */
export interface UseProjectAnimationsReturn {
  newBranches: Set<string>;
  fadingOutBranches: Set<string>;
  deletingBranches: Set<string>;
  animatingCounts: Map<string, 'up' | 'down'>;
  previousTaskCounts: Record<string, number>;
  isInitialLoad: boolean;
  setDeletingBranches: React.Dispatch<React.SetStateAction<Set<string>>>;
  setFadingOutBranches: React.Dispatch<React.SetStateAction<Set<string>>>;
}

/**
 * Dialog types for project operations
 */
export type ProjectDialogType = 'create' | 'edit' | 'delete' | 'createBranch' | 'deleteBranch';

/**
 * Project form data structure (re-exported from componentTypes for convenience)
 */
import type { ProjectFormData, DeleteBranchDialogState } from './componentTypes';
export type { ProjectFormData, DeleteBranchDialogState };

/**
 * Return type for useProjectDialogs hook
 * Manages all project dialog states and operations
 */
export interface UseProjectDialogsReturn {
  showCreate: boolean;
  showEdit: Project | null;
  showDelete: Project | null;
  showCreateBranch: Project | null;
  showDeleteBranch: DeleteBranchDialogState | null;
  form: ProjectFormData;
  saving: boolean;
  setSaving: (saving: boolean) => void;
  openCreateDialog: () => void;
  openEditDialog: (project: Project) => void;
  openDeleteDialog: (project: Project) => void;
  openCreateBranchDialog: (project: Project) => void;
  openDeleteBranchDialog: (dialogState: DeleteBranchDialogState) => void;
  closeDialog: (type: ProjectDialogType) => void;
  updateForm: (updates: Partial<ProjectFormData>) => void;
  setForm: React.Dispatch<React.SetStateAction<ProjectFormData>>;
}