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
// WebSocket Animation Service Types
// =============================================================================

/**
 * Animation trigger types for WebSocket events
 */
export type AnimationTriggerType = 'created' | 'updated' | 'deleted' | 'completed';

/**
 * Animation event structure
 */
export interface AnimationEvent {
  type: AnimationTriggerType;
  entity: string;
  entityId: string;
  data?: any;
  metadata?: any;
}

// =============================================================================
// Notification Service Types
// =============================================================================

export type NotificationType = 'success' | 'error' | 'info' | 'warning';

/**
 * Entity types across the system (MERGED from multiple sources)
 */
export type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';

/**
 * Event types across the system (MERGED from multiple sources)
 * Includes all possible event types from WebSocketNotificationService and changePoolService
 */
export type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned' | 'archived' | 'restored';

export interface NotificationOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  icon?: string;
  showBrowserNotification?: boolean;
}

// =============================================================================
// Authentication Service Types
// =============================================================================

/**
 * Keycloak token response structure
 */
export interface KeycloakTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  refresh_expires_in: number;
  token_type: string;
}

// =============================================================================
// Toast Event Bus Types
// =============================================================================

/**
 * Toast event types
 */
export type ToastEventType = 'success' | 'error' | 'warning' | 'info';

/**
 * Toast event structure
 */
export interface ToastEvent {
  type: ToastEventType;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// =============================================================================
// Change Pool Service Types
// =============================================================================

/**
 * Change notification structure for component subscriptions
 */
export interface ChangeNotification {
  entityType: EntityType;
  entityId: string;
  eventType: EventType;
  userId: string;
  data?: any;
  timestamp: number;
}

/**
 * Component subscription structure for change notifications
 */
export interface ComponentSubscription {
  componentId: string;
  entityTypes: EntityType[];
  entityIds?: string[]; // Specific entity IDs to watch (optional)
  projectId?: string;   // Filter by project
  branchId?: string;    // Filter by branch
  taskId?: string;      // Filter by task
  callback: (notification: ChangeNotification) => void;
}

// =============================================================================
// Token Service Types
// =============================================================================

/**
 * Request payload for generating a new API token
 */
export interface GenerateTokenRequest {
  name: string;
  scopes: string[];
  expires_in_days: number;
  rate_limit?: number;
}

/**
 * API token response structure
 */
export interface TokenResponse {
  id: string;
  name: string;
  token?: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  last_used_at?: string;
  usage_count: number;
  rate_limit?: number;
  is_active: boolean;
}

/**
 * Response for listing all tokens
 */
export interface TokenListResponse {
  data: TokenResponse[];
  total: number;
}