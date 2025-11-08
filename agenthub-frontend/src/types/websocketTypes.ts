/**
 * WebSocket Types
 * Consolidated types for WebSocket communication and protocol v2.0
 */

// =============================================================================
// WebSocket Configuration
// =============================================================================

export interface WebSocketConfig {
  maxReconnectAttempts: number;
  reconnectDelay: number;
  aiBufferTimeout: number;
  maxReconnectDelay: number;
  heartbeatInterval: number;
}

// =============================================================================
// WebSocket Protocol v2.0 Message Types
// =============================================================================

export interface WSMessage {
  id: string;
  version: '2.0';  // ONLY v2.0 supported
  type: 'update' | 'bulk' | 'sync' | 'heartbeat' | 'error';
  timestamp: string;
  sequence: number;
  payload: {
    entity: string;
    action: string;
    data: {
      id?: string;  // Direct data ID access
      primary: { id?: string; [key: string]: any } | any[];
      cascade?: {
        branches?: any[];
        tasks?: any[];
        projects?: any[];
        subtasks?: any[];
        contexts?: any[];
      };
      [key: string]: any;  // Allow other dynamic properties
    };
  };
  metadata: {
    source: 'mcp-ai' | 'user' | 'system';
    userId?: string;
    sessionId?: string;
    correlationId?: string;
    batchId?: string;
    entity_type?: string;
    entity_id?: string;
    event_type?: string;
    // Project-specific metadata
    project_title?: string;
    project_name?: string;
    // Task-specific metadata
    task_title?: string;
    parent_task_title?: string;
    // Subtask-specific metadata
    subtask_title?: string;
    // Branch-specific metadata
    branch_title?: string;
    parent_branch_title?: string;
    parent_branch_id?: string;
  };
}