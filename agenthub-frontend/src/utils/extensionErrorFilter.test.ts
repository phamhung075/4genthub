/**
 * Test for Extension Error Filter
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  isExtensionError,
  handlePotentialExtensionError,
  initializeExtensionErrorFilter
} from './extensionErrorFilter';

describe('extensionErrorFilter', () => {
  let originalConsoleError: typeof console.error;
  let originalConsoleWarn: typeof console.warn;

  beforeEach(() => {
    originalConsoleError = console.error;
    originalConsoleWarn = console.warn;
    console.error = vi.fn();
    console.warn = vi.fn();
  });

  afterEach(() => {
    console.error = originalConsoleError;
    console.warn = originalConsoleWarn;
  });

  describe('isExtensionError', () => {
    it('should detect runtime.lastError messages', () => {
      const error = new Error('Unchecked runtime.lastError: Could not establish connection. Receiving end does not exist.');
      expect(isExtensionError(error)).toBe(true);
    });

    it('should detect chrome-extension URLs', () => {
      const error = new Error('Script error');
      error.stack = 'Error at chrome-extension://abc123/content.js';
      expect(isExtensionError(error)).toBe(true);
    });

    it('should detect extension context invalidated errors', () => {
      const error = new Error('Extension context invalidated');
      expect(isExtensionError(error)).toBe(true);
    });

    it('should not flag normal application errors', () => {
      const error = new Error('Network request failed');
      expect(isExtensionError(error)).toBe(false);
    });

    it('should handle string error messages', () => {
      expect(isExtensionError('runtime.lastError: Connection failed')).toBe(true);
      expect(isExtensionError('Normal error message')).toBe(false);
    });
  });

  describe('handlePotentialExtensionError', () => {
    it('should return true for extension errors', () => {
      const error = new Error('runtime.lastError occurred');
      expect(handlePotentialExtensionError(error)).toBe(true);
    });

    it('should return false for non-extension errors', () => {
      const error = new Error('Application error');
      expect(handlePotentialExtensionError(error)).toBe(false);
    });
  });

  describe('initializeExtensionErrorFilter', () => {
    it('should initialize and return cleanup function', () => {
      const cleanup = initializeExtensionErrorFilter();
      expect(typeof cleanup).toBe('function');
      cleanup();
    });

    it('should filter extension errors from console.error', () => {
      // Set up mock before initialization
      const mockError = vi.fn();
      const originalError = console.error;
      console.error = mockError;

      const cleanup = initializeExtensionErrorFilter();

      // Reset mock after initialization
      mockError.mockClear();

      // Test extension error (should be filtered)
      console.error('runtime.lastError: Could not establish connection');
      expect(mockError).not.toHaveBeenCalled();

      // Test normal error (should not be filtered)
      console.error('Normal application error');
      expect(mockError).toHaveBeenCalledWith('Normal application error');

      cleanup();
      console.error = originalError;
    });
  });
});