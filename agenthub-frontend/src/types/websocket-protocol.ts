/**
 * WebSocket Protocol v2.0 - Type-Safe Communication Models
 *
 * SINGLE SOURCE OF TRUTH for WebSocket message structure
 * - Defines exact payload structure for each entity/action combination
 * - Enforces required fields at compile-time
 * - Prevents runtime errors from missing/incorrect data
 * - Self-documenting API contract
 *
 * USAGE:
 * - Backend: Generate Python Pydantic models from these types
 * - Frontend: Import and use for type-safe message handling
 * - Validation: Use Zod schemas (generated from these types) for runtime validation
 */

// =============================================================================
// ENTITY PAYLOAD MODELS - CRUD Operations
// =============================================================================

/**
 * PROJECT PAYLOADS
 */
export interface ProjectCreatePayload {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectUpdatePayload {
  id: string;
  name: string;
  description?: string;
  updated_at?: string;
}

export interface ProjectDeletePayload {
  id: string;           // REQUIRED for frontend handler
  name: string;         // For toast notification
}

/**
 * BRANCH PAYLOADS
 */
export interface BranchCreatePayload {
  id: string;
  name: string;
  git_branch_name: string;
  project_id: string;
  description?: string;
  status?: string;
  created_at?: string;
}

export interface BranchUpdatePayload {
  id: string;
  name: string;
  git_branch_name: string;
  project_id: string;
  description?: string;
  status?: string;
  updated_at?: string;
}

export interface BranchDeletePayload {
  id: string;           // REQUIRED for frontend handler
  name: string;         // For toast notification
  project_id: string;   // For cache invalidation
}

/**
 * TASK PAYLOADS
 */
export interface TaskCreatePayload {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  git_branch_id: string;
  assignees?: string[];
  labels?: string[];
  created_at?: string;
}

export interface TaskUpdatePayload {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  git_branch_id: string;
  assignees?: string[];
  labels?: string[];
  updated_at?: string;
}

export interface TaskDeletePayload {
  id: string;                   // REQUIRED for frontend handler
  title: string;                // For toast notification
  git_branch_id?: string;       // For cache invalidation
}

export interface TaskCompletePayload {
  id: string;
  title: string;
  status: 'done';
  completion_summary?: string;
  testing_notes?: string;
  completed_at?: string;
}

/**
 * SUBTASK PAYLOADS
 */
export interface SubtaskCreatePayload {
  id: string;
  title: string;
  description?: string;
  status: string;
  task_id: string;
  progress_percentage?: number;
  created_at?: string;
  updated_at?: string;  // ✅ ADDED: Backend includes this field (websocket_protocol.py:224)
}

export interface SubtaskUpdatePayload {
  id: string;
  title: string;
  description?: string;
  status: string;
  task_id: string;
  progress_percentage?: number;
  created_at?: string;  // ✅ ADDED: Backend includes this field (websocket_protocol.py:235)
  updated_at?: string;
}

export interface SubtaskDeletePayload {
  id: string;           // REQUIRED for frontend handler
  title?: string;       // For toast notification
  task_id: string;      // For cache invalidation
}

export interface SubtaskCompletePayload {
  id: string;
  title: string;
  status: 'done';
  task_id: string;
  completion_summary?: string;
  progress_percentage: 100;
  created_at?: string;   // ✅ ADDED: Backend includes this field (websocket_protocol.py:268)
  updated_at?: string;   // ✅ ADDED: Backend includes this field (websocket_protocol.py:269)
  completed_at?: string;
}

// =============================================================================
// ACTION-SPECIFIC PAYLOAD UNIONS
// =============================================================================

/**
 * CREATE action payloads (all entities)
 */
export type CreatePayload =
  | { entity: 'project'; data: ProjectCreatePayload }
  | { entity: 'branch'; data: BranchCreatePayload }
  | { entity: 'task'; data: TaskCreatePayload }
  | { entity: 'subtask'; data: SubtaskCreatePayload };

/**
 * UPDATE action payloads (all entities)
 */
export type UpdatePayload =
  | { entity: 'project'; data: ProjectUpdatePayload }
  | { entity: 'branch'; data: BranchUpdatePayload }
  | { entity: 'task'; data: TaskUpdatePayload }
  | { entity: 'subtask'; data: SubtaskUpdatePayload };

/**
 * DELETE action payloads (all entities)
 */
export type DeletePayload =
  | { entity: 'project'; data: ProjectDeletePayload }
  | { entity: 'branch'; data: BranchDeletePayload }
  | { entity: 'task'; data: TaskDeletePayload }
  | { entity: 'subtask'; data: SubtaskDeletePayload };

/**
 * COMPLETE action payloads (task and subtask only)
 */
export type CompletePayload =
  | { entity: 'task'; data: TaskCompletePayload }
  | { entity: 'subtask'; data: SubtaskCompletePayload };

// =============================================================================
// WEBSOCKET MESSAGE STRUCTURE (v2.0)
// =============================================================================

/**
 * WebSocket metadata - contextual information
 */
export interface WSMetadata {
  source: 'mcp-ai' | 'user' | 'system';
  userId?: string;
  sessionId?: string;
  correlationId?: string;

  // Entity context
  entity_type?: string;
  entity_id?: string;
  event_type?: string;

  // Entity-specific metadata
  project_id?: string;
  git_branch_id?: string;
  task_id?: string;

  // Display metadata (for toasts)
  project_name?: string;
  project_title?: string;  // Alias for project_name
  branch_title?: string;
  task_title?: string;
  subtask_title?: string;

  timestamp?: string;
}

/**
 * WebSocket payload structure
 */
export interface WSPayload<T = any> {
  entity: 'project' | 'branch' | 'task' | 'subtask' | 'context' | 'agent';
  action: 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned';
  data: {
    primary: T;           // Main entity data (MUST include 'id' field)
    cascade?: {           // Related entities updated by this action
      branches?: any[];
      tasks?: any[];
      subtasks?: any[];
      projects?: any[];
      contexts?: any[];
    };
  };
}

/**
 * Complete WebSocket message (v2.0 protocol)
 */
export interface WSMessage<T = any> {
  id: string;
  version: '2.0';
  type: 'update' | 'bulk' | 'sync' | 'heartbeat' | 'error';
  timestamp: string;
  sequence: number;
  payload: WSPayload<T>;
  metadata: WSMetadata;
}

// =============================================================================
// TYPE-SAFE MESSAGE CONSTRUCTORS
// =============================================================================

/**
 * Type-safe message for PROJECT operations
 */
export type ProjectMessage =
  | WSMessage<ProjectCreatePayload>
  | WSMessage<ProjectUpdatePayload>
  | WSMessage<ProjectDeletePayload>;

/**
 * Type-safe message for BRANCH operations
 */
export type BranchMessage =
  | WSMessage<BranchCreatePayload>
  | WSMessage<BranchUpdatePayload>
  | WSMessage<BranchDeletePayload>;

/**
 * Type-safe message for TASK operations
 */
export type TaskMessage =
  | WSMessage<TaskCreatePayload>
  | WSMessage<TaskUpdatePayload>
  | WSMessage<TaskDeletePayload>
  | WSMessage<TaskCompletePayload>;

/**
 * Type-safe message for SUBTASK operations
 */
export type SubtaskMessage =
  | WSMessage<SubtaskCreatePayload>
  | WSMessage<SubtaskUpdatePayload>
  | WSMessage<SubtaskDeletePayload>
  | WSMessage<SubtaskCompletePayload>;

// =============================================================================
// TYPE GUARDS - Runtime Type Checking
// =============================================================================

/**
 * Check if payload has required 'id' field
 */
export function hasId(data: any): data is { id: string } {
  return data && typeof data === 'object' && typeof data.id === 'string' && data.id.length > 0;
}

/**
 * Validate project delete payload
 */
export function isProjectDeletePayload(data: any): data is ProjectDeletePayload {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    typeof data.name === 'string'
  );
}

/**
 * Validate branch delete payload
 */
export function isBranchDeletePayload(data: any): data is BranchDeletePayload {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    typeof data.name === 'string' &&
    typeof data.project_id === 'string'
  );
}

/**
 * Validate task delete payload
 */
export function isTaskDeletePayload(data: any): data is TaskDeletePayload {
  return (
    data !== null &&
    data !== undefined &&
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    typeof data.title === 'string'
  );
}

/**
 * Validate subtask delete payload
 */
export function isSubtaskDeletePayload(data: any): data is SubtaskDeletePayload {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    typeof data.task_id === 'string'
  );
}

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validate WebSocket message structure
 */
export function isValidWSMessage(msg: any): msg is WSMessage {
  return (
    msg &&
    typeof msg === 'object' &&
    msg.version === '2.0' &&
    msg.payload &&
    msg.payload.entity &&
    msg.payload.action &&
    msg.payload.data &&
    msg.payload.data.primary
  );
}

/**
 * Extract entity ID from message (with fallback to metadata)
 */
export function getEntityId(msg: WSMessage): string | null {
  // Primary: Get from payload.data.primary.id
  if (hasId(msg.payload.data.primary)) {
    return msg.payload.data.primary.id;
  }

  // Fallback: Get from metadata.entity_id
  if (msg.metadata?.entity_id) {
    return msg.metadata.entity_id;
  }

  return null;
}

/**
 * Get display name from payload (for toasts)
 */
export function getDisplayName(msg: WSMessage): string {
  const { entity, data } = msg.payload;
  const primary = data.primary as any;

  // Try common name fields
  if (primary.name) return primary.name;
  if (primary.title) return primary.title;
  if (primary.git_branch_name) return primary.git_branch_name;

  // Fallback to metadata
  if (msg.metadata?.branch_title) return msg.metadata.branch_title;
  if (msg.metadata?.task_title) return msg.metadata.task_title;
  if (msg.metadata?.subtask_title) return msg.metadata.subtask_title;

  // Last resort: entity type + ID
  const id = getEntityId(msg);
  return `${entity} ${id?.substring(0, 8) || 'unknown'}`;
}

// =============================================================================
// PATTERN ENFORCEMENT
// =============================================================================

/**
 * Required fields for DELETE payloads (enforced pattern)
 *
 * ALL delete payloads MUST include:
 * 1. id: string - Entity identifier (REQUIRED for cache operations)
 * 2. name/title: string - Display name (REQUIRED for toast notifications)
 * 3. parent_id?: string - Parent entity for cache invalidation (if applicable)
 */
export type DeletePayloadPattern = {
  id: string;                    // REQUIRED
  name?: string;                 // REQUIRED (or 'title')
  title?: string;                // REQUIRED (or 'name')
  project_id?: string;           // For branches
  git_branch_id?: string;        // For tasks
  task_id?: string;              // For subtasks
};

/**
 * Validate delete payload follows required pattern
 */
export function validateDeletePayload(data: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check required: id
  if (!data?.id || typeof data.id !== 'string') {
    errors.push('Missing required field: id (string)');
  }

  // Check required: name OR title
  if (!data?.name && !data?.title) {
    errors.push('Missing required field: name or title (string)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
