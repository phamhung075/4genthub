import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WSMessage } from '../../services/WebSocketClient';

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

const webSocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    connected: (state, action: PayloadAction<{ connectionId?: string }>) => {
      state.isConnected = true;
      state.isReconnecting = false;
      state.error = null;
      state.reconnectAttempts = 0;
      state.connectionId = action.payload.connectionId || null;
      state.lastHeartbeat = new Date().toISOString();
    },

    disconnected: (state) => {
      state.isConnected = false;
      state.isReconnecting = true;
      state.connectionId = null;
    },

    reconnecting: (state, action: PayloadAction<{ attempt: number }>) => {
      state.isReconnecting = true;
      state.reconnectAttempts = action.payload.attempt;
    },

    reconnectFailed: (state) => {
      state.isReconnecting = false;
      state.error = 'Failed to reconnect to WebSocket server';
    },

    error: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
    },

    messageReceived: (state, action: PayloadAction<WSMessage>) => {
      const message = action.payload;

      // Update last message
      state.lastMessage = message;

      // Handle heartbeat
      if (message.type === 'heartbeat') {
        state.lastHeartbeat = message.timestamp;
        return;
      }

      // Add to message queue (keep last 50 messages for debugging)
      state.messageQueue.push(message);
      if (state.messageQueue.length > 50) {
        state.messageQueue.shift();
      }

      // Clear error on successful message
      if (state.error) {
        state.error = null;
      }
    },

    clearError: (state) => {
      state.error = null;
    },

    clearMessageQueue: (state) => {
      state.messageQueue = [];
    },

    updateHeartbeat: (state) => {
      state.lastHeartbeat = new Date().toISOString();
    },
  },
});

export const {
  connected,
  disconnected,
  reconnecting,
  reconnectFailed,
  error,
  messageReceived,
  clearError,
  clearMessageQueue,
  updateHeartbeat,
} = webSocketSlice.actions;

export default webSocketSlice.reducer;

// Selectors
export const selectWebSocketState = (state: { websocket: WebSocketState }) => state.websocket;
export const selectIsConnected = (state: { websocket: WebSocketState }) => state.websocket.isConnected;
export const selectIsReconnecting = (state: { websocket: WebSocketState }) => state.websocket.isReconnecting;
export const selectWebSocketError = (state: { websocket: WebSocketState }) => state.websocket.error;
export const selectLastMessage = (state: { websocket: WebSocketState }) => state.websocket.lastMessage;
export const selectMessageQueue = (state: { websocket: WebSocketState }) => state.websocket.messageQueue;
export const selectReconnectAttempts = (state: { websocket: WebSocketState }) => state.websocket.reconnectAttempts;
export const selectLastHeartbeat = (state: { websocket: WebSocketState }) => state.websocket.lastHeartbeat;