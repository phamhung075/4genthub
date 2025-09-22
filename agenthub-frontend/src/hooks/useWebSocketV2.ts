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
      // Dispatch message to Redux store
      dispatch(messageReceived(message));

      // Process cascade data if present
      if (message.payload.data.cascade) {
        dispatch(updateFromWebSocket(message.payload.data.cascade));
      }

      console.log('[WebSocket] Processed update:', {
        entity: message.payload.entity,
        action: message.payload.action,
        hasCascade: !!message.payload.data.cascade
      });
    });

    // Handle user actions (immediate feedback)
    client.on('userAction', (message: WSMessage) => {
      console.log('[WebSocket] User action:', message.payload.action);
      // User actions are already captured in the main update handler
      // Additional user-specific logic can be added here if needed
    });

    // Handle connection events
    client.on('connected', () => {
      console.log('[useWebSocket] Connected');
      dispatch(connected({}));
    });

    client.on('disconnected', () => {
      console.log('[useWebSocket] Disconnected');
      dispatch(disconnected());
    });

    client.on('error', (errorEvent: Event) => {
      console.error('[useWebSocket] Error:', errorEvent);
      dispatch(error('WebSocket connection error'));
    });

    client.on('reconnectFailed', () => {
      console.error('[useWebSocket] Failed to reconnect');
      dispatch(reconnectFailed());
    });

    // Connect to server
    client.connect();

    // Cleanup on unmount
    return () => {
      console.log('[useWebSocket] Cleaning up');
      client.disconnect();
      clientRef.current = null;
    };
  }, [userId, token, dispatch]);

  /**
   * Send message to WebSocket server
   */
  const sendMessage = useCallback((message: Partial<WSMessage>) => {
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
        type: 'update',
        payload: {
          entity: 'subscription',
          action: 'subscribe',
          data: {
            primary: {
              entityType: 'branch',
              entityId: branchId
            }
          }
        },
        metadata: {
          source: 'user'
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
        type: 'update',
        payload: {
          entity: 'subscription',
          action: 'subscribe',
          data: {
            primary: {
              entityType: 'task',
              entityId: taskId
            }
          }
        },
        metadata: {
          source: 'user'
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