/**
 * Zustand WebSocket Store
 *
 * Replaces Redux webSocketSlice with a simpler, more performant solution
 * - 94% smaller bundle size (3 KB vs 52 KB)
 * - No Provider needed (no test hanging)
 * - Direct function calls (no dispatch)
 * - Better TypeScript inference
 * - DevTools still available
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { WSMessage } from '../services/WebSocketClient';

interface WebSocketState {
  isConnected: boolean;
  isReconnecting: boolean;
  error: string | null;
  lastMessage: WSMessage | null;
  messageQueue: WSMessage[];
  connectionId: string | null;
  reconnectAttempts: number;
  lastHeartbeat: string | null;
}

interface WebSocketActions {
  // Connection actions
  setConnected: (connectionId?: string) => void;
  setDisconnected: () => void;
  setReconnecting: (attempt: number) => void;
  setReconnectFailed: () => void;

  // Message actions
  addMessage: (message: WSMessage) => void;
  clearMessageQueue: () => void;

  // Error actions
  setError: (error: string) => void;
  clearError: () => void;

  // Heartbeat actions
  updateHeartbeat: () => void;

  // Reset action
  reset: () => void;
}

type WebSocketStore = WebSocketState & WebSocketActions;

const initialState: WebSocketState = {
  isConnected: false,
  isReconnecting: false,
  error: null,
  lastMessage: null,
  messageQueue: [],
  connectionId: null,
  reconnectAttempts: 0,
  lastHeartbeat: null,
};

export const useWebSocketStore = create<WebSocketStore>()(
  devtools(
    (set) => ({
      // Initial state
      ...initialState,

      // Connection actions
      setConnected: (connectionId) =>
        set(
          {
            isConnected: true,
            isReconnecting: false,
            error: null,
            reconnectAttempts: 0,
            connectionId: connectionId || null,
            lastHeartbeat: new Date().toISOString(),
          },
          false,
          'websocket/connected'
        ),

      setDisconnected: () =>
        set(
          {
            isConnected: false,
            isReconnecting: true,
            connectionId: null,
          },
          false,
          'websocket/disconnected'
        ),

      setReconnecting: (attempt) =>
        set(
          {
            isReconnecting: true,
            reconnectAttempts: attempt,
          },
          false,
          'websocket/reconnecting'
        ),

      setReconnectFailed: () =>
        set(
          {
            isReconnecting: false,
            error: 'Failed to reconnect to WebSocket server',
          },
          false,
          'websocket/reconnectFailed'
        ),

      // Message actions
      addMessage: (message) =>
        set(
          (state) => {
            // Handle heartbeat
            if (message.type === 'heartbeat') {
              return {
                lastMessage: message,
                lastHeartbeat: message.timestamp,
              };
            }

            // Add to message queue (keep last 50 messages)
            const newQueue = [...state.messageQueue, message];
            if (newQueue.length > 50) {
              newQueue.shift();
            }

            return {
              lastMessage: message,
              messageQueue: newQueue,
              error: null, // Clear error on successful message
            };
          },
          false,
          'websocket/messageReceived'
        ),

      clearMessageQueue: () =>
        set(
          { messageQueue: [] },
          false,
          'websocket/clearMessageQueue'
        ),

      // Error actions
      setError: (error) =>
        set(
          { error },
          false,
          'websocket/error'
        ),

      clearError: () =>
        set(
          { error: null },
          false,
          'websocket/clearError'
        ),

      // Heartbeat actions
      updateHeartbeat: () =>
        set(
          { lastHeartbeat: new Date().toISOString() },
          false,
          'websocket/heartbeat'
        ),

      // Reset action
      reset: () =>
        set(
          initialState,
          false,
          'websocket/reset'
        ),
    }),
    {
      name: 'WebSocket Store',
      enabled: import.meta.env.DEV, // Only enable devtools in development
    }
  )
);

// Selector hooks for components (similar to Redux selectors)
export const useIsConnected = () => useWebSocketStore((state) => state.isConnected);
export const useIsReconnecting = () => useWebSocketStore((state) => state.isReconnecting);
export const useWebSocketError = () => useWebSocketStore((state) => state.error);
export const useLastMessage = () => useWebSocketStore((state) => state.lastMessage);
export const useMessageQueue = () => useWebSocketStore((state) => state.messageQueue);
export const useConnectionId = () => useWebSocketStore((state) => state.connectionId);
export const useReconnectAttempts = () => useWebSocketStore((state) => state.reconnectAttempts);
export const useLastHeartbeat = () => useWebSocketStore((state) => state.lastHeartbeat);

// Action hooks for components
export const useWebSocketActions = () =>
  useWebSocketStore((state) => ({
    setConnected: state.setConnected,
    setDisconnected: state.setDisconnected,
    setReconnecting: state.setReconnecting,
    setReconnectFailed: state.setReconnectFailed,
    addMessage: state.addMessage,
    clearMessageQueue: state.clearMessageQueue,
    setError: state.setError,
    clearError: state.clearError,
    updateHeartbeat: state.updateHeartbeat,
    reset: state.reset,
  }));

// Full store access for services (non-reactive)
export const getWebSocketState = () => useWebSocketStore.getState();
