/**
 * WebSocket Service for Real-time Data Synchronization
 *
 * This service manages the WebSocket connection to the backend and provides
 * real-time updates to the UI when data changes on the server.
 */

import { toastEventBus } from './toastEventBus';
import { notificationDeduplicationService } from './notificationDeduplicationService';
import logger from '../utils/logger';
import Cookies from 'js-cookie';

// Entity and event types for WebSocket messages
type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';
type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'archived' | 'restored';

export interface WebSocketMessage {
  type: string;
  data?: any;
  event_type?: string;
  level?: string;
  context_id?: string;
  user_id?: string;
  timestamp?: string;
  metadata?: {
    entity_type?: string;
    entity_id?: string;
    event_type?: string;
    project_id?: string;
    git_branch_id?: string;
    parent_task_id?: string;
    context_level?: string;
    [key: string]: any;
  };
}

export type DataChangeHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private tokenMonitorInterval: NodeJS.Timeout | null = null;
  private handlers: Map<string, Set<DataChangeHandler>> = new Map();
  private isConnecting = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds

  /**
   * Connect to the WebSocket server
   */
  async connect(token?: string): Promise<void> {
    // Check all possible states that indicate we shouldn't connect
    if (this.ws?.readyState === WebSocket.OPEN ||
        this.ws?.readyState === WebSocket.CONNECTING ||
        this.isConnecting) {
      logger.debug('WebSocket already connected or connecting');
      return;
    }

    this.isConnecting = true;

    try {
      // Get the backend URL from environment or use default
      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      // Use Vite environment variables consistently
      const apiUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';
      const backendHost = apiUrl.replace(/^https?:\/\//, '');
      // WebSocket endpoint is at /ws/realtime
      const wsUrl = `${wsProtocol}://${backendHost}/ws/realtime`;

      // Add auth token to query params if available
      let finalUrl = wsUrl;
      if (token) {
        finalUrl = `${wsUrl}?token=${encodeURIComponent(token)}`;
      } else {
        // Try to get token from cookies (primary storage for auth tokens)
        const storedToken = Cookies.get('access_token');
        if (storedToken) {
          finalUrl = `${wsUrl}?token=${encodeURIComponent(storedToken)}`;
        }
      }

      logger.info('Connecting to WebSocket:', wsUrl);
      this.ws = new WebSocket(finalUrl);

      this.ws.onopen = () => {
        logger.info('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;

        // Log connection status
        if (!token && !Cookies.get('access_token')) {
          logger.info('Connected as anonymous user');
        }

        // Start heartbeat
        this.startHeartbeat();

        // Start token monitoring for automatic reconnection
        this.startTokenMonitoring();

        // Subscribe to user updates by default
        this.subscribe('user');
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          logger.debug('🔔 WebSocket message received:', message);
          this.handleMessage(message);
        } catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        logger.error('WebSocket error:', error);
        this.isConnecting = false;
      };

      this.ws.onclose = (event) => {
        logger.info('WebSocket disconnected:', event.code, event.reason);
        this.isConnecting = false;
        this.stopHeartbeat();

        // Stop token monitoring on disconnect (will restart on successful reconnect)
        this.stopTokenMonitoring();

        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopHeartbeat();
    this.stopTokenMonitoring();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  /**
   * Reconnect with a new authentication token
   * This is useful when the access token is refreshed
   */
  async reconnectWithNewToken(newToken: string): Promise<void> {
    logger.info('Reconnecting WebSocket with new authentication token');

    // Disconnect existing connection
    this.disconnect();

    // Wait a brief moment for cleanup
    await new Promise(resolve => setTimeout(resolve, 100));

    // Connect with new token
    await this.connect(newToken);
  }

  /**
   * Monitor cookie changes and automatically reconnect with new tokens
   * This provides automatic WebSocket reconnection when auth tokens are refreshed
   */
  private startTokenMonitoring(): void {
    // Check for token changes every 30 seconds
    const checkInterval = setInterval(() => {
      const currentToken = Cookies.get('access_token');

      // If no token exists and we're connected, disconnect
      if (!currentToken && this.isConnected()) {
        logger.info('Access token removed - disconnecting WebSocket');
        this.disconnect();
        return;
      }

      // If token exists but we're not connected, try to connect
      if (currentToken && !this.isConnected()) {
        logger.info('Access token detected - attempting WebSocket connection');
        this.connect(currentToken).catch(error => {
          logger.error('Failed to connect WebSocket with detected token:', error);
        });
      }
    }, 30000); // Check every 30 seconds

    // Store interval for cleanup
    this.tokenMonitorInterval = checkInterval;
  }

  /**
   * Stop token monitoring
   */
  private stopTokenMonitoring(): void {
    if (this.tokenMonitorInterval) {
      clearInterval(this.tokenMonitorInterval);
      this.tokenMonitorInterval = null;
    }
  }

  /**
   * Subscribe to a specific scope of updates
   */
  private subscribe(scope: 'global' | 'user' | 'project' | 'branch' | 'task', filters?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      logger.warn('Cannot subscribe: WebSocket not connected');
      return;
    }

    const message = {
      type: 'subscribe',
      scope,
      filters: filters || {}
    };

    this.ws.send(JSON.stringify(message));
    logger.debug('Subscribed to', scope, 'updates');
  }

  /**
   * Register a handler for specific event types
   */
  on(eventType: string, handler: DataChangeHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }

    this.handlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(eventType);
        }
      }
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: WebSocketMessage): void {
    logger.debug('WebSocket message received:', message);

    // Handle system messages
    switch (message.type) {
      case 'welcome':
      case 'auth_success':
      case 'auth_info':
      case 'subscribed':
      case 'subscription_updated':
      case 'pong':
        // System messages, no need to forward to handlers
        return;
      case 'error':
        logger.error('WebSocket error:', message);
        return;
    }

    // Handle data change notifications
    if (message.type === 'status_update' || message.event_type) {
      // Determine the entity type from metadata
      const entityType = message.metadata?.entity_type || 'unknown';
      const eventType = message.metadata?.event_type || message.event_type || 'updated';


      // Show notification to user
      this.showNotification(message, entityType, eventType);

      // Notify all handlers for this entity type
      const handlers = this.handlers.get(entityType);
      if (handlers) {
        handlers.forEach(handler => handler(message));
      }

      // Also notify handlers for the specific event type
      const eventHandlers = this.handlers.get(`${entityType}:${eventType}`);
      if (eventHandlers) {
        eventHandlers.forEach(handler => handler(message));
      }

      // Notify universal handlers
      const universalHandlers = this.handlers.get('*');
      if (universalHandlers) {
        universalHandlers.forEach(handler => handler(message));
      }
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), this.maxReconnectDelay);

    logger.debug(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }

  /**
   * Show notification for data changes
   */
  private showNotification(message: WebSocketMessage, entityType: string, eventType: string): void {
    // Skip notifications for certain events
    if (eventType === 'heartbeat' || message.type === 'heartbeat') {
      return;
    }

    // Skip notifications for branch creation/deletion - handled by ProjectList component
    // This prevents duplicate notifications
    if (entityType === 'branch' && (eventType === 'created' || eventType === 'deleted')) {
      return;
    }

    // Get entity name from data
    const entityName = message.data?.title ||
                      message.data?.name ||
                      message.data?.git_branch_name ||
                      message.data?.description?.substring(0, 50);

    const entityId = message.metadata?.entity_id || message.context_id;
    const userName = message.user_id || message.data?.user_id;

    // Don't show notification if it's from the current user's action
    // (They already know what they did)
    // Extract user ID from access token in cookies if available
    const accessToken = Cookies.get('access_token');
    let currentUserId = null;
    if (accessToken) {
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        currentUserId = payload.sub || payload.user_id;
      } catch (error) {
        logger.debug('Could not decode access token for user ID comparison');
      }
    }

    if (currentUserId && userName === currentUserId) {
      // Still update the UI, but don't show notification
      return;
    }


    // Show the notification using toast event bus
    this.showToastNotification(
      entityType as EntityType,
      eventType as EventType,
      entityName,
      entityId,
      userName
    );
  }

  /**
   * Show toast notification for entity changes
   */
  private showToastNotification(
    entityType: EntityType,
    eventType: EventType,
    entityName?: string,
    entityId?: string,
    userName?: string
  ): void {
    // CRITICAL: Apply client-side deduplication to prevent 7x duplicate notifications
    const shouldShow = notificationDeduplicationService.shouldShowNotification(
      entityType,
      eventType,
      entityName,
      entityId,
      userName,
      { timestamp: Date.now() } // Additional context for hash uniqueness
    );

    if (!shouldShow) {
      logger.debug('🚫 WebSocket notification blocked by deduplication service', {
        entityType,
        eventType,
        entityName,
        entityId,
        userName
      });
      return; // Exit early - don't show duplicate notification
    }

    const name = entityName || `${entityType} #${entityId?.substring(0, 8)}`;
    const user = userName || 'Another user';

    logger.debug('✅ WebSocket notification allowed by deduplication service', {
      entityType,
      eventType,
      entityName,
      entityId,
      userName
    });

    // Determine the notification based on event type
    switch (eventType) {
      case 'created':
        toastEventBus.success(
          `New ${entityType} created`,
          `${user} created "${name}"`
        );
        break;
      case 'updated':
        toastEventBus.info(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} updated`,
          `${user} modified "${name}"`
        );
        break;
      case 'deleted':
        toastEventBus.warning(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} deleted`,
          `${user} deleted "${name}"`
        );
        // Also show browser notification for deletions
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification(`${entityType.charAt(0).toUpperCase() + entityType.slice(1)} deleted`, {
            body: `${user} deleted "${name}"`,
            icon: '/favicon.ico',
            tag: `${entityType}-${eventType}-${entityId}`
          });
        }
        break;
      case 'completed':
        toastEventBus.success(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} completed`,
          `${user} completed "${name}"`
        );
        break;
      case 'archived':
        toastEventBus.info(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} archived`,
          `${user} archived "${name}"`
        );
        break;
      case 'restored':
        toastEventBus.info(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} restored`,
          `${user} restored "${name}"`
        );
        break;
      default:
        toastEventBus.info(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} ${eventType}`,
          `${user} ${eventType} "${name}"`
        );
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Subscribe to project-specific updates
   */
  subscribeToProject(projectId: string): void {
    this.subscribe('project', { project_id: projectId });
  }

  /**
   * Subscribe to branch-specific updates
   */
  subscribeToBranch(branchId: string): void {
    this.subscribe('branch', { git_branch_id: branchId });
  }

  /**
   * Subscribe to task-specific updates
   */
  subscribeToTask(taskId: string): void {
    this.subscribe('task', { task_id: taskId });
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Track if we've already scheduled auto-connect
let autoConnectScheduled = false;

// Auto-connect when the service is imported (only once, even with StrictMode)
if (typeof window !== 'undefined' && !autoConnectScheduled) {
  autoConnectScheduled = true;
  // Connect after a short delay to ensure auth is initialized
  setTimeout(() => {
    // Double-check we're not already connected before attempting
    if (!websocketService.isConnected()) {
      websocketService.connect().catch(logger.error);
    }
  }, 1000);
}