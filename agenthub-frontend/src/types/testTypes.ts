/**
 * Test & Mock Types
 * Centralized type definitions for test files and mock implementations
 */

import { WSMessage } from '../services/WebSocketClient';

// =============================================================================
// WebSocket Mock Server Types
// =============================================================================

/**
 * Mock WebSocket server configuration
 */
export interface MockWebSocketServerConfig {
  url: string;
  autoConnect: boolean;
  connectionDelay: number;
  heartbeatInterval: number;
  reconnectDelay: number;
  maxReconnectAttempts: number;
  simulateNetworkIssues: boolean;
}

/**
 * Client subscription structure for mock server
 */
export interface ClientSubscription {
  clientId: string;
  scope: 'branch' | 'task' | 'project' | 'global';
  filters: Record<string, any>;
  active: boolean;
}

/**
 * Mock WebSocket client structure
 */
export interface MockWebSocketClient {
  id: string;
  connected: boolean;
  subscriptions: ClientSubscription[];
  messageQueue: WSMessage[];
  lastSeen: number;
}