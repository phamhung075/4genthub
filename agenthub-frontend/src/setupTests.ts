/**
 * Setup file for Vitest tests
 * Configures testing environment and global test utilities
 *
 * INTENTIONAL: This file overrides console.error for test environment setup
 * Must use native console methods to suppress noisy React warnings during tests
 * The override is necessary for clean test output and doesn't affect application code
 */

import { afterEach, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';
import { resetWebSocketStore } from './tests/zustand-utils';
import { cleanup } from '@testing-library/react';

// Enable auto-mocking for animation services
vi.mock('./services/AnimationFactory');
vi.mock('./services/taskDeletionTracker');
vi.mock('./services/branchDeletionTracker');

// Cleanup after each test
afterEach(() => {
  cleanup();
  resetWebSocketStore(); // Reset Zustand store to prevent state pollution
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;

// Suppress console errors in tests unless explicitly enabled
const originalError = console.error;
beforeEach(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render') ||
        args[0].includes('Warning: useLayoutEffect') ||
        args[0].includes('Not implemented: HTMLFormElement.prototype.submit'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterEach(() => {
  console.error = originalError;
});
