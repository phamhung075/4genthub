/**
 * Zustand Test Utilities
 *
 * Helper functions for testing components that use Zustand stores.
 * Provides store reset and mocking capabilities for isolated test environments.
 *
 * Usage:
 *   import { resetWebSocketStore, mockWebSocketStore } from './zustand-utils';
 *
 *   beforeEach(() => {
 *     resetWebSocketStore(); // Reset to initial state
 *   });
 *
 *   test('connected state', () => {
 *     mockWebSocketStore({ isConnected: true });
 *     // Test component...
 *   });
 */

import { useWebSocketStore } from '../store/websocket';

/**
 * Reset WebSocket store to initial state
 *
 * This should be called in afterEach() to ensure test isolation.
 * Prevents state pollution between tests.
 */
export function resetWebSocketStore(): void {
  useWebSocketStore.getState().reset();
}

/**
 * Mock WebSocket store state for testing
 *
 * Allows setting specific state values for testing different scenarios.
 *
 * @param state - Partial state to merge with current store state
 *
 * @example
 * mockWebSocketStore({ isConnected: true, error: null });
 */
export function mockWebSocketStore(state: Partial<ReturnType<typeof useWebSocketStore.getState>>): void {
  useWebSocketStore.setState(state);
}

/**
 * Get current WebSocket store state (for assertions)
 *
 * @returns Current store state
 *
 * @example
 * expect(getWebSocketStoreState().isConnected).toBe(true);
 */
export function getWebSocketStoreState() {
  return useWebSocketStore.getState();
}
