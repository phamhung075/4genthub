import { useEffect, useRef, useCallback, useState } from 'react';
import { WebSocketClient, WSMessage } from '../services/WebSocketClient';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  connected,
  disconnected,
  reconnecting,
  reconnectFailed,
  error,
  messageReceived,
  selectIsConnected,
  selectIsReconnecting,
  selectWebSocketError,
} from '../store/slices/webSocketSlice';
import { updateFromWebSocket } from '../store/slices/cascadeSlice';
import { webSocketAnimationService } from '../services/WebSocketAnimationService';
import { initializeWebSocketIntegration } from '../services/changePoolService';
import { notificationService } from '../services/notificationService';
import logger from '../utils/logger';


// Global WebSocket instance to ensure singleton
let globalWebSocketClient: WebSocketClient | null = null;

/**
 * React Hook for WebSocket v2.0
 * Provides WebSocket connection management and real-time updates
 * Implements singleton pattern to prevent multiple connections
 */
export function useWebSocket(userId: string, token: string) {
  const dispatch = useAppDispatch();
  const clientRef = useRef<WebSocketClient | null>(null);

  // Get WebSocket state from Redux store
  const isConnected = useAppSelector(selectIsConnected);
  const isReconnecting = useAppSelector(selectIsReconnecting);
  const wsError = useAppSelector(selectWebSocketError);

  useEffect(() => {
    logger.debug('[useWebSocket] 🚀 DEBUG: Hook called with params:', {
      hasUserId: !!userId,
      hasToken: !!token,
      userIdLength: userId?.length,
      tokenLength: token?.length,
      userId: userId,
      timestamp: new Date().toISOString()
    }, 'useWebSocketV2.ts');

    if (!userId || !token) {
      logger.warn('[useWebSocket] ❌ Cannot connect - missing credentials:', {
        hasUserId: !!userId,
        hasToken: !!token,
        userIdLength: userId?.length,
        tokenLength: token?.length,
        message: 'WebSocket connection aborted due to missing credentials'
      }, 'useWebSocketV2.ts');
      return;
    }

    logger.debug('[useWebSocket] ✅ Credentials validated, proceeding with connection setup', undefined, 'useWebSocketV2.ts');

    // Check if we already have a global client with the same credentials
    if (globalWebSocketClient) {
      const existingClientUserId = (globalWebSocketClient as any).userId;
      const existingClientToken = (globalWebSocketClient as any).token;

      if (existingClientUserId === userId && existingClientToken === token) {
        logger.debug('[useWebSocket] Reusing existing WebSocket client', undefined, 'useWebSocketV2.ts');
        clientRef.current = globalWebSocketClient;

        // CRITICAL FIX: Initialize services even when reusing existing client
        // These initializations are idempotent and set up event listeners for this component instance
        webSocketAnimationService.init(globalWebSocketClient);
        const cleanupChangePool = initializeWebSocketIntegration(globalWebSocketClient);
        const cleanupNotifications = notificationService.initializeWebSocketListener(globalWebSocketClient);

        // Return cleanup function for this component instance
        return () => {
          logger.debug('[useWebSocket] Component cleanup (reused client)', undefined, 'useWebSocketV2.ts');
          cleanupChangePool();
          cleanupNotifications();
          clientRef.current = null;
        };
      } else {
        logger.debug('[useWebSocket] Credentials changed, disconnecting old client', undefined, 'useWebSocketV2.ts');
        globalWebSocketClient.disconnect();
        globalWebSocketClient = null;
      }
    }

    logger.debug('[useWebSocket] Creating new WebSocket client with credentials:', {
      userId,
      tokenLength: token.length,
      timestamp: new Date().toISOString()
    }, 'useWebSocketV2.ts');

    // Create new WebSocket client
    const client = new WebSocketClient(userId, token);
    clientRef.current = client;
    globalWebSocketClient = client;

    // Handle updates (both immediate and batched)
    client.on('update', (message: WSMessage) => {
      logger.debug('[useWebSocket] 🎯 🚨 DELETE DEBUG: UPDATE EVENT RECEIVED:', {
        messageId: message.id,
        entity: message.payload.entity,
        action: message.payload.action,
        source: message.metadata?.source,
        hasCascade: !!message.payload.data.cascade
      }, 'useWebSocketV2.ts');

      // Special detailed logging for DELETE operations
      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE UPDATE EVENT RECEIVED IN useWebSocket HOOK:', {
          messageId: message.id,
          entity: message.payload.entity,
          action: message.payload.action,
          source: message.metadata?.source,
          hasCascade: !!message.payload.data.cascade,
          primaryData: message.payload.data.primary,
          info: 'About to dispatch to Redux store...'
        }, 'useWebSocketV2.ts');
      }

      // Dispatch message to Redux store
      dispatch(messageReceived(message));

      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('✅ DELETE message dispatched to Redux store', undefined, 'useWebSocketV2.ts');
      }

      // Process cascade data if present
      if (message.payload.data.cascade) {
        logger.debug('[useWebSocket] 🔄 Processing cascade data', undefined, 'useWebSocketV2.ts');
        dispatch(updateFromWebSocket(message.payload.data.cascade));

        if (message.payload?.action?.toLowerCase().includes('delete')) {
          logger.warn('✅ DELETE cascade data processed', undefined, 'useWebSocketV2.ts');
        }
      }

      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('✅ DELETE update processed successfully in useWebSocket', undefined, 'useWebSocketV2.ts');
      } else {
        logger.debug('[useWebSocket] ✅ Processed update successfully', undefined, 'useWebSocketV2.ts');
      }
    });

    // Handle user actions (immediate feedback)
    client.on('userAction', (message: WSMessage) => {
      logger.debug('[WebSocket] User action:', message.payload.action, 'useWebSocketV2.ts');
      // User actions are already captured in the main update handler
      // Additional user-specific logic can be added here if needed
    });

    // Handle connection events
    client.on('connected', () => {
      logger.info('[useWebSocket] ✅ CONNECTED - WebSocket ready', undefined, 'useWebSocketV2.ts');
      dispatch(connected({}));
    });

    client.on('disconnected', () => {
      logger.warn('[useWebSocket] ❌ DISCONNECTED', undefined, 'useWebSocketV2.ts');
      dispatch(disconnected());
    });

    client.on('error', (errorEvent: Event) => {
      logger.error('[useWebSocket] ❌ ERROR:', errorEvent, 'useWebSocketV2.ts');
      dispatch(error('WebSocket connection error'));
    });

    client.on('reconnectFailed', () => {
      logger.error('[useWebSocket] ❌ RECONNECT FAILED', undefined, 'useWebSocketV2.ts');
      dispatch(reconnectFailed());
    });

    client.on('authenticationFailed', (reason: string) => {
      logger.error('[useWebSocket] ❌ AUTHENTICATION FAILED:', reason, 'useWebSocketV2.ts');
      dispatch(error(`WebSocket authentication failed: ${reason}`));
      // You may want to trigger a re-authentication flow here
      // For example: dispatch a logout action or redirect to login
    });

    // Initialize the animation service with the WebSocket client
    webSocketAnimationService.init(client);

    // Initialize the change pool service with the WebSocket client
    logger.debug('[useWebSocket] 🔧 DEBUG: About to call initializeWebSocketIntegration', undefined, 'useWebSocketV2.ts');
    logger.debug('[useWebSocket] 🔧 DEBUG: Client object:', client, 'useWebSocketV2.ts');
    logger.debug('[useWebSocket] 🔧 DEBUG: Client has .on method:', typeof client.on === 'function', 'useWebSocketV2.ts');
    logger.debug('[useWebSocket] 🔧 DEBUG: Update listener count BEFORE changePool:', client.listenerCount('update'), 'useWebSocketV2.ts');

    const cleanupChangePool = initializeWebSocketIntegration(client);

    logger.debug('[useWebSocket] 🔧 DEBUG: initializeWebSocketIntegration returned', undefined, 'useWebSocketV2.ts');
    logger.debug('[useWebSocket] 🔧 DEBUG: Update listener count AFTER changePool:', client.listenerCount('update'), 'useWebSocketV2.ts');
    logger.debug('[useWebSocket] 🔧 DEBUG: Cleanup function type:', typeof cleanupChangePool, 'useWebSocketV2.ts');

    // Initialize the unified notification service with the WebSocket client
    const cleanupNotifications = notificationService.initializeWebSocketListener(client);

    // Connect to server
    client.connect();

    // Cleanup on unmount - but don't disconnect the global singleton
    return () => {
      logger.debug('[useWebSocket] Component cleanup (keeping WebSocket connected)', undefined, 'useWebSocketV2.ts');
      // Don't disconnect the global client - it should persist
      // Only clean up local references
      cleanupChangePool();
      cleanupNotifications();
      clientRef.current = null;
    };
  }, [userId, token, dispatch]);

  /**
   * Send message to WebSocket server
   */
  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (clientRef.current) {
      clientRef.current.send(message);
    } else {
      logger.error('[useWebSocket] Client not initialized', undefined, 'useWebSocketV2.ts');
    }
  }, []);

  /**
   * Manually reconnect
   */
  const reconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.resetReconnectAttempts();
      clientRef.current.connect();
    }
  }, []);

  /**
   * Disconnect WebSocket (for logout or cleanup)
   */
  const disconnect = useCallback(() => {
    logger.info('[useWebSocket] Disconnecting WebSocket (explicit disconnect)', undefined, 'useWebSocketV2.ts');
    if (clientRef.current) {
      clientRef.current.disconnect();
      // Also clear the global singleton on explicit disconnect (e.g., logout)
      if (globalWebSocketClient === clientRef.current) {
        globalWebSocketClient = null;
      }
    }
  }, []);

  return {
    isConnected,
    isReconnecting,
    error: wsError ? new Error(wsError) : null,
    sendMessage,
    reconnect,
    disconnect
  };
}

/**
 * Specialized hook for branch real-time updates
 */
export function useBranchWebSocket(userId: string, token: string, branchId?: string) {
  const { sendMessage, ...wsState } = useWebSocket(userId, token);

  const subscribeToBranch = useCallback(() => {
    if (branchId) {
      sendMessage({
        type: 'subscribe',
        scope: 'branch',
        filters: {
          branch_id: branchId
        }
      });
    }
  }, [branchId, sendMessage]);

  useEffect(() => {
    if (wsState.isConnected && branchId) {
      subscribeToBranch();
    }
  }, [wsState.isConnected, branchId, subscribeToBranch]);

  return {
    ...wsState,
    sendMessage
  };
}

/**
 * Specialized hook for task real-time updates
 */
export function useTaskWebSocket(userId: string, token: string, taskId?: string) {
  const { sendMessage, ...wsState } = useWebSocket(userId, token);

  const subscribeToTask = useCallback(() => {
    if (taskId) {
      sendMessage({
        type: 'subscribe',
        scope: 'task',
        filters: {
          task_id: taskId
        }
      });
    }
  }, [taskId, sendMessage]);

  useEffect(() => {
    if (wsState.isConnected && taskId) {
      subscribeToTask();
    }
  }, [wsState.isConnected, taskId, subscribeToTask]);

  return {
    ...wsState,
    sendMessage,
    updateTask: (update: any) => {
      sendMessage({
        type: 'update',
        payload: {
          entity: 'task',
          action: 'update',
          data: {
            primary: { id: taskId, ...update }
          }
        },
        metadata: {
          source: 'user'
        }
      });
    }
  };
}
