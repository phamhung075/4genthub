/**
 * Service Types
 * Consolidated types for service layer functionality
 */

import type { TaskSummary } from './taskTypes';

// =============================================================================
// API Service Types
// =============================================================================

export interface TaskSummariesResponse {
  tasks: TaskSummary[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// =============================================================================
// Notification Service Types
// =============================================================================

export type NotificationType = 'success' | 'error' | 'info' | 'warning';
export type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';
export type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned' | 'archived' | 'restored';

export interface NotificationOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  icon?: string;
  showBrowserNotification?: boolean;
}