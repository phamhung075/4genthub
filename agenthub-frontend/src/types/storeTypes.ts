/**
 * Redux Store Types
 * Consolidated types for Redux store configuration and state management
 */

import { store } from '../store';

/**
 * Root state type derived from the store
 */
export type RootState = ReturnType<typeof store.getState>;

/**
 * App dispatch type for typed dispatching
 */
export type AppDispatch = typeof store.dispatch;