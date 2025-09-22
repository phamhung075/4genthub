import { configureStore } from '@reduxjs/toolkit';
import webSocketReducer from './slices/webSocketSlice';
import cascadeReducer from './slices/cascadeSlice';

export const store = configureStore({
  reducer: {
    websocket: webSocketReducer,
    cascade: cascadeReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization checks
        ignoredActions: [
          'websocket/messageReceived',
          'websocket/error',
          'cascade/updateFromWebSocket',
        ],
        // Ignore these field paths in all actions
        ignoredActionsPaths: ['meta.arg', 'payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['websocket.lastMessage', 'websocket.messageQueue'],
      },
    }),
  devTools: import.meta.env.MODE !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;