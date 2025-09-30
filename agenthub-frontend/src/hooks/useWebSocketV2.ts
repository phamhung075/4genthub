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
    console.log('[useWebSocket] 🚀 DEBUG: Hook called with params:', {
      hasUserId: !!userId,
      hasToken: !!token,
      userIdLength: userId?.length,
      tokenLength: token?.length,
      userId: userId,
      timestamp: new Date().toISOString()
    });

    if (!userId || !token) {
      console.warn('[useWebSocket] ❌ Cannot connect - missing credentials:', {
        hasUserId: !!userId,
        hasToken: !!token,
        userIdLength: userId?.length,
        tokenLength: token?.length,
        message: 'WebSocket connection aborted due to missing credentials'
      });
      return;
    }

    console.log('[useWebSocket] ✅ Credentials validated, proceeding with connection setup');

    // Check if we already have a global client with the same credentials
    if (globalWebSocketClient) {
      const existingClientUserId = (globalWebSocketClient as any).userId;
      const existingClientToken = (globalWebSocketClient as any).token;

      if (existingClientUserId === userId && existingClientToken === token) {
        console.log('[useWebSocket] Reusing existing WebSocket client');
        clientRef.current = globalWebSocketClient;

        // CRITICAL FIX: Initialize services even when reusing existing client
        // These initializations are idempotent and set up event listeners for this component instance
        webSocketAnimationService.init(globalWebSocketClient);
        const cleanupChangePool = initializeWebSocketIntegration(globalWebSocketClient);
        const cleanupNotifications = notificationService.initializeWebSocketListener(globalWebSocketClient);

        // Return cleanup function for this component instance
        return () => {
          console.log('[useWebSocket] Component cleanup (reused client)');
          cleanupChangePool();
          cleanupNotifications();
          clientRef.current = null;
        };
      } else {
        console.log('[useWebSocket] Credentials changed, disconnecting old client');
        globalWebSocketClient.disconnect();
        globalWebSocketClient = null;
      }
    }

    console.log('[useWebSocket] Creating new WebSocket client with credentials:', {
      userId,
      tokenLength: token.length,
      timestamp: new Date().toISOString()
    });

    // Create new WebSocket client
    const client = new WebSocketClient(userId, token);
    clientRef.current = client;
    globalWebSocketClient = client;

    // Handle updates (both immediate and batched)
    client.on('update', (message: WSMessage) => {
      console.log('[useWebSocket] 🎯 🚨 DELETE DEBUG: UPDATE EVENT RECEIVED:', {
        messageId: message.id,
        entity: message.payload.entity,
        action: message.payload.action,
        source: message.metadata?.source,
        hasCascade: !!message.payload.data.cascade
      });

      // Special detailed logging for DELETE operations
      if (message.payload?.action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE UPDATE EVENT RECEIVED IN useWebSocket HOOK:');
        console.warn('  Message ID:', message.id);
        console.warn('  Entity:', message.payload.entity);
        console.warn('  Action:', message.payload.action);
        console.warn('  Source:', message.metadata?.source);
        console.warn('  Has Cascade:', !!message.payload.data.cascade);
        console.warn('  Primary Data:', message.payload.data.primary);
        console.warn('  About to dispatch to Redux store...');
      }

      // Dispatch message to Redux store
      dispatch(messageReceived(message));

      if (message.payload?.action?.toLowerCase().includes('delete')) {
        console.warn('✅ DELETE message dispatched to Redux store');
      }

      // Process cascade data if present
      if (message.payload.data.cascade) {
        console.log('[useWebSocket] 🔄 Processing cascade data');
        dispatch(updateFromWebSocket(message.payload.data.cascade));

        if (message.payload?.action?.toLowerCase().includes('delete')) {
          console.warn('✅ DELETE cascade data processed');
        }
      }

      if (message.payload?.action?.toLowerCase().includes('delete')) {
        console.warn('✅ DELETE update processed successfully in useWebSocket');
      } else {
        console.log('[useWebSocket] ✅ Processed update successfully');
      }
    });

    // Handle user actions (immediate feedback)
    client.on('userAction', (message: WSMessage) => {
      console.log('[WebSocket] User action:', message.payload.action);
      // User actions are already captured in the main update handler
      // Additional user-specific logic can be added here if needed
    });

    // Handle connection events
    client.on('connected', () => {
      console.log('[useWebSocket] ✅ CONNECTED - WebSocket ready');
      dispatch(connected({}));
    });

    client.on('disconnected', () => {
      console.log('[useWebSocket] ❌ DISCONNECTED');
      dispatch(disconnected());
    });

    client.on('error', (errorEvent: Event) => {
      console.error('[useWebSocket] ❌ ERROR:', errorEvent);
      dispatch(error('WebSocket connection error'));
    });

    client.on('reconnectFailed', () => {
      console.error('[useWebSocket] ❌ RECONNECT FAILED');
      dispatch(reconnectFailed());
    });

    client.on('authenticationFailed', (reason: string) => {
      console.error('[useWebSocket] ❌ AUTHENTICATION FAILED:', reason);
      dispatch(error(`WebSocket authentication failed: ${reason}`));
      // You may want to trigger a re-authentication flow here
      // For example: dispatch a logout action or redirect to login
    });

    // Initialize the animation service with the WebSocket client
    webSocketAnimationService.init(client);

    // Initialize the change pool service with the WebSocket client
    console.log('[useWebSocket] 🔧 DEBUG: About to call initializeWebSocketIntegration');
    console.log('[useWebSocket] 🔧 DEBUG: Client object:', client);
    console.log('[useWebSocket] 🔧 DEBUG: Client has .on method:', typeof client.on === 'function');
    console.log('[useWebSocket] 🔧 DEBUG: Update listener count BEFORE changePool:', client.listenerCount('update'));

    const cleanupChangePool = initializeWebSocketIntegration(client);

    console.log('[useWebSocket] 🔧 DEBUG: initializeWebSocketIntegration returned');
    console.log('[useWebSocket] 🔧 DEBUG: Update listener count AFTER changePool:', client.listenerCount('update'));
    console.log('[useWebSocket] 🔧 DEBUG: Cleanup function type:', typeof cleanupChangePool);

    // Initialize the unified notification service with the WebSocket client
    const cleanupNotifications = notificationService.initializeWebSocketListener(client);

    // Connect to server
    client.connect();

    // Cleanup on unmount - but don't disconnect the global singleton
    return () => {
      console.log('[useWebSocket] Component cleanup (keeping WebSocket connected)');
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
      console.error('[useWebSocket] Client not initialized');
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
    console.log('[useWebSocket] Disconnecting WebSocket (explicit disconnect)');
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
