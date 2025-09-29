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