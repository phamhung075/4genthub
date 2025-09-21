/**
 * WebSocket Service for Real-time Data Synchronization
 *
 * This service manages the WebSocket connection to the backend and provides
 * real-time updates to the UI when data changes on the server.
 */

import { toastEventBus } from './toastEventBus';
import { changePoolService } from './changePoolService';
import logger from '../utils/logger';

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

      // Enhanced token detection and debugging
      let authToken = token;
      if (!authToken) {
        // Try cookies first (primary storage method)
        const cookieValue = document.cookie
          .split('; ')
          .find(row => row.startsWith('access_token='))
          ?.split('=')[1];
        if (cookieValue) {
          authToken = cookieValue;
          logger.debug('WebSocket: Found auth token in cookies');
        } else {
          // Try localStorage as fallback
          authToken = localStorage.getItem('access_token');
          if (authToken) {
            logger.debug('WebSocket: Found auth token in localStorage');
          }
        }
      } else {
        logger.debug('WebSocket: Using provided auth token');
      }

      // Add detailed logging for token status
      if (authToken) {
        // Log token info without exposing the actual token
        logger.info('WebSocket: Connecting with authentication token', {
          tokenLength: authToken.length,
          tokenPreview: authToken.substring(0, 20) + '...',
          wsUrl: wsUrl
        });
      } else {
        logger.warn('WebSocket: No authentication token found! Connection may fail.', {
          localStorage: !!localStorage.getItem('access_token'),
          cookies: document.cookie.includes('access_token='),
          wsUrl: wsUrl
        });
      }

      // Build final URL with token
      let finalUrl = wsUrl;
      if (authToken) {
        finalUrl = `${wsUrl}?token=${encodeURIComponent(authToken)}`;
      }

      logger.info('WebSocket: Attempting connection to:', finalUrl.replace(/token=[^&]+/, 'token=***'));
      this.ws = new WebSocket(finalUrl);

      this.ws.onopen = () => {
        logger.info('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;

        // Log connection status
        if (!token && !localStorage.getItem('access_token')) {
          logger.info('Connected as anonymous user');
        }

        // Start heartbeat
        this.startHeartbeat();

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
        logger.error('WebSocket error occurred:', error);
        this.isConnecting = false;
      };

      this.ws.onclose = (event) => {
        logger.info('WebSocket disconnected:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        this.isConnecting = false;
        this.stopHeartbeat();

        // Enhanced close code handling with specific error messages
        if (event.code === 4001) {
          logger.error('WebSocket authentication failed! Invalid or missing JWT token.');
          logger.error('Debug info:', {
            hasTokenInLocalStorage: !!localStorage.getItem('access_token'),
            hasTokenInCookies: document.cookie.includes('access_token='),
            tokenUsed: authToken ? 'yes' : 'no'
          });

          // If we have a token but auth failed, it might be expired
          // Try to trigger a token refresh if we're in a React context
          if (authToken) {
            logger.info('WebSocket: Token exists but auth failed - may be expired. Triggering refresh event.');
            window.dispatchEvent(new CustomEvent('websocket-auth-failed', {
              detail: { code: event.code, reason: 'Token authentication failed' }
            }));
          }

          // Don't auto-reconnect on auth failure
          return;
        } else if (event.code === 1006) {
          logger.error('WebSocket connection failed - server may be down or unreachable');
        } else if (event.code === 1008) {
          logger.error('WebSocket connection terminated due to policy violation');
        } else if (event.code === 1011) {
          logger.error('WebSocket connection terminated due to server error');
        }

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

      // Notify changePoolService for component updates
      if (entityType === 'task' || entityType === 'subtask') {
        const changeNotification = {
          entityType: entityType as any,
          entityId: message.metadata?.entity_id || '',
          eventType: eventType as any,
          userId: message.user_id || message.metadata?.user_id || '',
          data: message.data,
          metadata: message.metadata,
          timestamp: message.timestamp || new Date().toISOString()
        };

        changePoolService.processChange(changeNotification);
      }

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
    const currentUserId = localStorage.getItem('user_id');
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
    const name = entityName || `${entityType} #${entityId?.substring(0, 8)}`;
    const user = userName || 'Another user';

    console.log(`🌐 WebSocket: showToastNotification called for ${entityType}:${eventType}`, {
      entityType,
      eventType,
      entityName,
      entityId,
      userName
    });

    // Determine the notification based on event type
    switch (eventType) {
      case 'created':
        console.log('🌐 WebSocket: Calling toastEventBus.success for created event');
        toastEventBus.success(
          `New ${entityType} created`,
          `${user} created "${name}"`
        );
        break;
      case 'updated':
        console.log('🌐 WebSocket: Calling toastEventBus.info for updated event');
        toastEventBus.info(
          `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} updated`,
          `${user} modified "${name}"`
        );
        break;
      case 'deleted':
        console.log('🌐 WebSocket: Calling toastEventBus.warning for deleted event');
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
   * Debug method to check authentication and connection status
   */
  debugConnectionStatus(): void {
    // Use same token detection logic as connect method
    const cookieToken = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
    const localStorageToken = localStorage.getItem('access_token');
    const authToken = cookieToken || localStorageToken;

    logger.info('WebSocket Debug Status:', {
      connection: {
        state: this.ws?.readyState,
        stateText: this.ws?.readyState === WebSocket.CONNECTING ? 'CONNECTING' :
                   this.ws?.readyState === WebSocket.OPEN ? 'OPEN' :
                   this.ws?.readyState === WebSocket.CLOSING ? 'CLOSING' :
                   this.ws?.readyState === WebSocket.CLOSED ? 'CLOSED' : 'UNKNOWN',
        isConnecting: this.isConnecting,
        reconnectAttempts: this.reconnectAttempts
      },
      authentication: {
        hasToken: !!authToken,
        tokenLength: authToken?.length || 0,
        tokenSource: cookieToken ? 'cookies' : localStorageToken ? 'localStorage' : 'none',
        cookieAvailable: !!cookieToken,
        localStorageAvailable: !!localStorageToken
      },
      backend: {
        apiUrl: import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000',
        wsProtocol: window.location.protocol === 'https:' ? 'wss' : 'ws'
      }
    });
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

// Note: WebSocket connection is now managed by AuthContext
// This ensures proper authentication token is available before connecting
// Auto-connect removed to fix race condition with authentication loading