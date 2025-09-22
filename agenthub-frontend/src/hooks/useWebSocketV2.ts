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


/**
 * React Hook for WebSocket v2.0
 * Provides WebSocket connection management and real-time updates
 */
export function useWebSocket(userId: string, token: string) {
  const dispatch = useAppDispatch();
  const clientRef = useRef<WebSocketClient | null>(null);

  // Get WebSocket state from Redux store
  const isConnected = useAppSelector(selectIsConnected);
  const isReconnecting = useAppSelector(selectIsReconnecting);
  const wsError = useAppSelector(selectWebSocketError);

  useEffect(() => {
    if (!userId || !token) {
      console.warn('[useWebSocket] Missing userId or token');
      return;
    }

    // Create WebSocket client
    const client = new WebSocketClient(userId, token);
    clientRef.current = client;

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

    // Initialize the animation service with the WebSocket client
    webSocketAnimationService.init(client);

    // Initialize the change pool service with the WebSocket client
    const cleanupChangePool = initializeWebSocketIntegration(client);

    // Initialize the unified notification service with the WebSocket client
    const cleanupNotifications = notificationService.initializeWebSocketListener(client);

    // Connect to server
    client.connect();

    // Cleanup on unmount
    return () => {
      console.log('[useWebSocket] Cleaning up');
      client.disconnect();
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
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
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
