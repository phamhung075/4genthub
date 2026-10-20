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
 * - Backend: the Go payload structs in agenthub_go/fastmcp/task_management/domain/websocket_protocol.go are kept in step with these
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
  project_id?: string;  // 🔥 CRITICAL FIX: For project cache invalidation
  assignees?: string[];
  labels?: string[];
  created_at?: string;
}

/**
 * A task update is a DELTA (PERF-05 ruling at 3ccf9b00): the id and `updated_at`, plus only the
 * fields the write changed. `details` is never carried - unbounded text - so a changed progress log
 * is signalled by `details_changed`, and the reader re-reads the row for it. A change set that would
 * exceed the byte cap is sent as `{id, refetch: true}` instead, carrying no fields to merge at all.
 */
export interface TaskUpdatePayload {
  id: string;
  updated_at?: string;
  details_changed?: boolean;
  refetch?: boolean;
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  git_branch_id?: string;
  assignees?: string[];
  labels?: string[];
}

export interface TaskDeletePayload {
  id: string;                   // REQUIRED for frontend handler
  title: string;                // For toast notification
  git_branch_id?: string;       // For cache invalidation
  project_id?: string;          // For project cache invalidation
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
  updated_at?: string;  // ✅ ADDED: Backend includes this field (agenthub_go/fastmcp/task_management/domain/websocket_protocol.go:322-333)
}

export interface SubtaskUpdatePayload {
  id: string;
  title: string;
  description?: string;
  status: string;
  task_id: string;
  progress_percentage?: number;
  created_at?: string;  // ✅ ADDED: Backend includes this field (agenthub_go/fastmcp/task_management/domain/websocket_protocol.go:335-346)
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
  created_at?: string;   // ✅ ADDED: Backend includes this field (agenthub_go/fastmcp/task_management/domain/websocket_protocol.go:372-382)
  updated_at?: string;   // ✅ ADDED: Backend includes this field (agenthub_go/fastmcp/task_management/domain/websocket_protocol.go:372-382)
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
// SEAT / ROOM PAYLOADS (seat-domain broadcasts)
// =============================================================================

/**
 * Seat event payload. The Go seat admin mutations emit this in the same v2
 * envelope; the client invalidates the seat react-query keys and animates the
 * row, so it does not need the full seat body.
 */
export interface SeatEventPayload {
  /** Stable id for cache/animation keying: '<room>/<seat_key>'. */
  id: string;
  /** Room slug; selects the seat query keys. */
  room: string;
  /** Seat member key within the room. */
  seat_key: string;
  /** Display name for the toast; falls back to seat_key. */
  name?: string;
}

/**
 * Room event payload (room create/delete, and company settings as id 'company').
 */
export interface RoomEventPayload {
  /** Room slug ('company' for the company settings change). */
  id: string;
  /** Room slug. */
  room: string;
  /** Display name for the toast. */
  name?: string;
}

/**
 * Notification payload. The client posts this through POST /api/v2/broadcast/notify; the server
 * delivers it on the realtime socket as payload.entity 'notification' with action 'notification',
 * live to a connected socket or replayed from the missed-notification store on reconnect. The
 * server copies data.primary through unchanged and carries entity_id and kind in metadata.
 */
export interface NotificationEventPayload {
  /** The message the human should see. */
  message: string;
  /** Who sent it: a seat key. */
  from?: string;
  room?: string;
  seat?: string;
  /** Free-form kind, for example 'notice'. */
  kind?: string;
}

// The frame carries metadata.entity_id, which the client uses as the dedupe key: it must be
// unique per notification, because two notifications posted with the same entity_id collapse
// into one inbox row (that is the idempotency the reconnect replay relies on).

/**
 * Safeguard alert payload: the stored `room_safeguard` row a state change is about.
 *
 * The server raises this on the realtime socket as payload.entity 'room_safeguard' with action and
 * event_type 'safeguard_alert', live to a connected socket or replayed from the missed-notification
 * store on reconnect (rigd-boundaries.md 7.3). The fields are the frame's own - the row's key parts
 * and its counters - so this payload names a ROW, not a message: the inbox line is composed from it
 * at the consumer, and metadata.entity_id is the row key, which is NOT unique per alert.
 *
 * `state` is ABSENT on the dead-man alert (7.3): that one is about the connector's own silence, which
 * no child reported, so it carries the machine scope's safeguard name and no state.
 *
 * The entity's `room_safeguard` names the ROW kind and `safeguard` names the client axis, so the two
 * are different things and are allowed to look alike: this row may report the safeguard NAMED
 * `roomguard`, and that name is one of the six the client has always sent - neither is derived from
 * the other, and a rename of one is not a rename of the other.
 */
export interface RoomSafeguardAlertPayload {
  /** The client-reported safeguard name: compact | watchdog | messages | roomguard | bridge | agent. */
  safeguard: string;
  /** The state the row moved to: stopped | silent | failing. Absent on the dead-man alert. */
  state?: string;
  /** The room the row is about; empty on the two machine-scoped names (bridge, agent). */
  room?: string;
  /** The connector - the machine - the row came from. */
  connector_id?: string;
  /** The row's restart counter. */
  restarts?: number;
  /** The row's heartbeat age in seconds. */
  age_s?: number;
}

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
export interface WSPayload<T = unknown> {
  entity: 'project' | 'branch' | 'task' | 'subtask' | 'context' | 'seat' | 'room';
  action: 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned';
  data: {
    primary: T;           // Main entity data (MUST include 'id' field)
    cascade?: {           // Related entities updated by this action
      branches?: unknown[];
      tasks?: unknown[];
      subtasks?: unknown[];
      projects?: unknown[];
      contexts?: unknown[];
    };
  };
}

/**
 * Complete WebSocket message (v2.0 protocol)
 */
export interface WSMessage<T = unknown> {
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
export function hasId(data: unknown): data is { id: string } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof data.id === 'string' &&
    data.id.length > 0
  );
}

/**
 * Validate project delete payload
 */
export function isProjectDeletePayload(data: unknown): data is ProjectDeletePayload {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    'name' in data &&
    typeof data.name === 'string'
  );
}

/**
 * Validate branch delete payload
 */
export function isBranchDeletePayload(data: unknown): data is BranchDeletePayload {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    'name' in data &&
    typeof data.name === 'string' &&
    'project_id' in data &&
    typeof data.project_id === 'string'
  );
}

/**
 * Validate task delete payload
 */
export function isTaskDeletePayload(data: unknown): data is TaskDeletePayload {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    'title' in data &&
    typeof data.title === 'string'
  );
}

/**
 * Validate subtask delete payload
 */
export function isSubtaskDeletePayload(data: unknown): data is SubtaskDeletePayload {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof data.id === 'string' &&
    data.id.length > 0 &&
    'task_id' in data &&
    typeof data.task_id === 'string'
  );
}

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validate WebSocket message structure
 */
export function isValidWSMessage(msg: unknown): msg is WSMessage {
  if (typeof msg !== 'object' || msg === null) return false;
  if (!('version' in msg) || msg.version !== '2.0') return false;
  if (!('payload' in msg)) return false;

  const payload = msg.payload;
  if (typeof payload !== 'object' || payload === null) return false;
  if (!('entity' in payload) || !payload.entity) return false;
  if (!('action' in payload) || !payload.action) return false;
  if (!('data' in payload)) return false;

  const data = payload.data;
  if (typeof data !== 'object' || data === null) return false;
  return 'primary' in data && Boolean(data.primary);
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
  const primary = data.primary;

  // Try common name fields
  if (typeof primary === 'object' && primary !== null) {
    if ('name' in primary && typeof primary.name === 'string' && primary.name) {
      return primary.name;
    }
    if ('title' in primary && typeof primary.title === 'string' && primary.title) {
      return primary.title;
    }
    if (
      'git_branch_name' in primary &&
      typeof primary.git_branch_name === 'string' &&
      primary.git_branch_name
    ) {
      return primary.git_branch_name;
    }
  }

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
export function validateDeletePayload(data: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (typeof data !== 'object' || data === null) {
    return {
      valid: false,
      errors: [
        'Missing required field: id (string)',
        'Missing required field: name or title (string)',
      ],
    };
  }

  // Check required: id
  if (!('id' in data) || typeof data.id !== 'string' || data.id.length === 0) {
    errors.push('Missing required field: id (string)');
  }

  // Check required: name OR title
  const hasName = 'name' in data && Boolean(data.name);
  const hasTitle = 'title' in data && Boolean(data.title);
  if (!hasName && !hasTitle) {
    errors.push('Missing required field: name or title (string)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
