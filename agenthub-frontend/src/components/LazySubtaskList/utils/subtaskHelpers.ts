// LazySubtaskList utility helper functions
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import type { Subtask } from "../../../api";
import type { SubtaskSummary } from "../../../types/taskTypes";
import type { SubtaskFilterOptions } from "../../../types/subtaskTypes";
import logger from "../../../utils/logger";

/**
 * Convert Subtask to SubtaskSummary
 * Used when creating summaries from full subtask objects
 */
export function subtaskToSummary(subtask: Subtask): SubtaskSummary {
  return {
    id: subtask.id,
    title: subtask.title,
    status: subtask.status,
    priority: subtask.priority,
    assignees: subtask.assignees,
    progress_percentage: subtask.progress_percentage
  };
}

/**
 * Check if a subtask ID has a valid UUID format
 * Prevents unnecessary API calls for invalid IDs
 */
export function isValidSubtaskId(subtaskId: string): boolean {
  if (!subtaskId || typeof subtaskId !== 'string') {
    return false;
  }

  // Basic UUID format check (36 characters with hyphens in correct positions)
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(subtaskId);
}

/**
 * Filter subtasks based on filter options
 */
export function filterSubtasks(
  subtasks: SubtaskSummary[],
  filterOptions: SubtaskFilterOptions
): SubtaskSummary[] {
  // Ensure subtasks is an array
  if (!Array.isArray(subtasks)) {
    logger.warn('filterSubtasks received non-array value:', subtasks);
    return [];
  }

  return subtasks.filter(subtask => {
    // Filter by status
    if (filterOptions.status?.length &&
        !filterOptions.status.includes(subtask.status)) {
      return false;
    }

    // Filter by priority
    if (filterOptions.priority?.length &&
        !filterOptions.priority.includes(subtask.priority)) {
      return false;
    }

    // Filter by assignees
    if (filterOptions.assignees?.length) {
      const hasMatchingAssignee = subtask.assignees?.some(assignee =>
        filterOptions.assignees!.includes(assignee)
      ) || false;
      if (!hasMatchingAssignee) {
        return false;
      }
    }

    // Filter by search term
    if (filterOptions.searchTerm) {
      const searchLower = filterOptions.searchTerm.toLowerCase();
      const titleMatch = subtask.title.toLowerCase().includes(searchLower);
      const assigneeMatch = subtask.assignees?.some(assignee =>
        assignee.toLowerCase().includes(searchLower)
      ) || false;

      if (!titleMatch && !assigneeMatch) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Calculate progress summary from subtask summaries
 */
export function calculateProgressSummary(subtasks: SubtaskSummary[]) {
  const total = subtasks.length;
  const completed = subtasks.filter(s => s.status === 'done').length;
  const inProgress = subtasks.filter(s =>
    ['in_progress', 'review', 'testing'].includes(s.status)
  ).length;
  const todo = subtasks.filter(s => s.status === 'todo').length;
  const blocked = subtasks.filter(s =>
    ['blocked', 'cancelled'].includes(s.status)
  ).length;

  return {
    total,
    completed,
    inProgress,
    todo,
    blocked,
    percentage: total > 0 ? Math.round((completed / total) * 100) : 0
  };
}

/**
 * Sort subtasks by field and direction
 */
export function sortSubtasks(
  subtasks: SubtaskSummary[],
  sortField: 'title' | 'status' | 'priority' | 'progress_percentage',
  direction: 'asc' | 'desc' = 'asc'
): SubtaskSummary[] {
  return [...subtasks].sort((a, b) => {
    let aValue: unknown = a[sortField];
    let bValue: unknown = b[sortField];

    // Handle priority sorting with custom order
    if (sortField === 'priority') {
      const priorityOrder = { low: 1, medium: 2, high: 3, urgent: 4 };
      aValue = priorityOrder[a.priority as keyof typeof priorityOrder] || 0;
      bValue = priorityOrder[b.priority as keyof typeof priorityOrder] || 0;
    }

    // Handle numeric values
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return direction === 'asc' ? aValue - bValue : bValue - aValue;
    }

    // Handle string values
    const aStr = String(aValue || '').toLowerCase();
    const bStr = String(bValue || '').toLowerCase();

    if (direction === 'asc') {
      return aStr.localeCompare(bStr);
    } else {
      return bStr.localeCompare(aStr);
    }
  });
}

/**
 * Detect changes between old and new subtask arrays
 * Returns change detection results for animations
 */
export function detectSubtaskChanges(
  oldSubtasks: SubtaskSummary[],
  newSubtasks: SubtaskSummary[]
): {
  created: Set<string>;
  updated: Set<string>;
  deleted: Set<string>;
} {
  const oldMap = new Map(oldSubtasks.map(s => [s.id, s]));
  const newMap = new Map(newSubtasks.map(s => [s.id, s]));

  const created = new Set<string>();
  const updated = new Set<string>();
  const deleted = new Set<string>();

  // Find created subtasks
  for (const [id, newSubtask] of newMap) {
    if (!oldMap.has(id)) {
      created.add(id);
    } else {
      // Check for updates
      const oldSubtask = oldMap.get(id)!;
      if (hasSubtaskChanged(oldSubtask, newSubtask)) {
        updated.add(id);
      }
    }
  }

  // Find deleted subtasks
  for (const [id] of oldMap) {
    if (!newMap.has(id)) {
      deleted.add(id);
    }
  }

  return { created, updated, deleted };
}

/**
 * Check if a subtask has changed (for update detection)
 */
function hasSubtaskChanged(oldSubtask: SubtaskSummary, newSubtask: SubtaskSummary): boolean {
  return (
    oldSubtask.title !== newSubtask.title ||
    oldSubtask.status !== newSubtask.status ||
    oldSubtask.priority !== newSubtask.priority ||
    oldSubtask.progress_percentage !== newSubtask.progress_percentage ||
    JSON.stringify(oldSubtask.assignees) !== JSON.stringify(newSubtask.assignees)
  );
}

/**
 * Generate branch URL (without subtask)
 */
export function generateBranchUrl(
  projectId: string,
  taskTreeId: string
): string {
  return `/dashboard/project/${projectId}/branch/${taskTreeId}`;
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Shape of the errors the API client throws: Axios errors carry `status`/`response.status`, plain
 * `Error`s carry `name`/`message`.
 */
interface ApiErrorLike {
  status?: number;
  name?: string;
  message?: string;
  response?: { status?: number };
}

/**
 * Narrow an unknown thrown value to the error fields the subtask code reads.
 */
export function isApiError(value: unknown): value is ApiErrorLike {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const response = 'response' in value ? value.response : undefined;
  const hasValidResponse =
    response === undefined ||
    (typeof response === 'object' &&
      response !== null &&
      (!('status' in response) || typeof response.status === 'number'));

  return (
    (!('status' in value) || typeof value.status === 'number') &&
    (!('name' in value) || typeof value.name === 'string') &&
    (!('message' in value) || typeof value.message === 'string') &&
    hasValidResponse
  );
}

/**
 * Narrow an API payload to a Subtask.
 *
 * The shared dialog types widen their subtask parameters to `unknown`; every caller in this feature
 * passes either a full record or its list summary (`SubtaskSummary`), so the dialog and hook code
 * narrows once here instead of casting at each property access. `task_id` is deliberately not
 * required: a subtask nested in a parent task payload carries `parent_task_id` instead (see
 * `Subtask.parent_task_id`), and the dialogs only read the fields checked below.
 */
export function isSubtask(value: unknown): value is Subtask {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  return (
    'id' in value && typeof value.id === 'string' &&
    'title' in value && typeof value.title === 'string' &&
    'status' in value && typeof value.status === 'string' &&
    'priority' in value && typeof value.priority === 'string'
  );
}

/**
 * Safe error logging for subtask operations
 */
export function logSubtaskError(
  operation: string,
  error: unknown,
  context?: Record<string, unknown>
): void {
  const apiError = isApiError(error) ? error : undefined;
  const status = apiError?.status ?? apiError?.response?.status;
  const message = apiError?.message ?? error;

  // Only log non-404 errors to avoid console noise
  if (status !== 404) {
    logger.error(`Subtask ${operation} error:`, {
      error: message,
      ...context
    });
  } else {
    logger.debug(`Subtask ${operation} not found (expected):`, {
      error: message,
      ...context
    });
  }
}

/**
 * Create empty subtask data state
 */
export function createEmptySubtaskDataState() {
  return {
    subtaskSummaries: [],
    fullSubtasks: new Map<string, Subtask>(),
    loading: false,
    error: null,
    loadingSubtasks: new Set<string>(),
    hasLoaded: false,
    subscriptionEnabled: false
  };
}
