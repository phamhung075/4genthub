import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  isExtensionError,
  handlePotentialExtensionError,
  filteredErrorHandler,
  filteredRejectionHandler,
  setupConsoleErrorFilter,
  initializeExtensionErrorFilter
} from '../../utils/extensionErrorFilter';
import logger from '../../utils/logger';

// Mock logger
vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}));

describe('extensionErrorFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('isExtensionError', () => {
    it('should detect runtime.lastError patterns', () => {
      expect(isExtensionError('runtime.lastError: Could not connect')).toBe(true);
      expect(isExtensionError('Uncaught runtime.lastError')).toBe(true);
      expect(isExtensionError('RUNTIME.LASTERROR')).toBe(true); // case insensitive
    });

    it('should detect connection error patterns', () => {
      expect(isExtensionError('Could not establish connection. Receiving end does not exist.')).toBe(true);
      expect(isExtensionError('could not establish connection. receiving end does not exist')).toBe(true);
    });

    it('should detect extension context errors', () => {
      expect(isExtensionError('Extension context invalidated')).toBe(true);
      expect(isExtensionError('Uncaught Error: Extension context invalidated')).toBe(true);
    });

    it('should detect extension URL patterns', () => {
      expect(isExtensionError('chrome-extension://abcdef/script.js')).toBe(true);
      expect(isExtensionError('moz-extension://abcdef/script.js')).toBe(true);
      expect(isExtensionError('safari-extension://abcdef/script.js')).toBe(true);
    });

    it('should detect message port errors', () => {
      expect(isExtensionError('The message port closed before a response was received.')).toBe(true);
    });

    it('should detect chrome URL access errors', () => {
      expect(isExtensionError('Cannot access a chrome:// URL')).toBe(true);
      expect(isExtensionError('Cannot access chrome://')).toBe(true);
    });

    it('should detect runtime availability errors', () => {
      expect(isExtensionError('chrome.runtime is not available')).toBe(true);
      expect(isExtensionError('browser.runtime is not available')).toBe(true);
    });

    it('should not detect non-extension errors', () => {
      expect(isExtensionError('Regular application error')).toBe(false);
      expect(isExtensionError('TypeError: Cannot read property of undefined')).toBe(false);
      expect(isExtensionError('Network request failed')).toBe(false);
    });

    it('should handle Error objects', () => {
      const extensionError = new Error('runtime.lastError: Connection failed');
      extensionError.stack = 'Error at chrome-extension://abc/background.js:10:5';
      expect(isExtensionError(extensionError)).toBe(true);

      const appError = new Error('Application specific error');
      appError.stack = 'Error at http://localhost:3000/app.js:20:10';
      expect(isExtensionError(appError)).toBe(false);
    });

    it('should handle ErrorEvent objects', () => {
      const extensionEvent = {
        message: 'Extension context invalidated',
        filename: 'chrome-extension://abc/content.js'
      } as ErrorEvent;
      expect(isExtensionError(extensionEvent)).toBe(true);

      const appEvent = {
        message: 'Syntax error',
        filename: 'http://localhost:3000/main.js'
      } as ErrorEvent;
      expect(isExtensionError(appEvent)).toBe(false);
    });

    it('should detect errors from extension scripts by source', () => {
      const error = new Error('Some generic error');
      error.stack = 'Error at chrome-extension://abc123/inject.js:15:20';
      expect(isExtensionError(error)).toBe(true);
    });
  });

  describe('handlePotentialExtensionError', () => {
    it('should filter extension errors and return true', () => {
      const result = handlePotentialExtensionError('runtime.lastError occurred', 'test context');
      expect(result).toBe(true);
      expect(logger.debug).toHaveBeenCalledWith(
        'Filtered browser extension error in test context',
        expect.objectContaining({
          error: 'runtime.lastError occurred',
          type: 'extension_error',
          filtered: true
        })
      );
    });

    it('should not filter non-extension errors and return false', () => {
      const result = handlePotentialExtensionError('Application error', 'test context');
      expect(result).toBe(false);
      expect(logger.debug).not.toHaveBeenCalled();
    });

    it('should handle Error objects', () => {
      const error = new Error('Extension context invalidated');
      error.stack = 'Error at chrome-extension://abc/script.js:10:5';
      
      const result = handlePotentialExtensionError(error);
      expect(result).toBe(true);
      expect(logger.debug).toHaveBeenCalledWith(
        'Filtered browser extension error',
        expect.objectContaining({
          error: 'Extension context invalidated',
          source: error.stack,
          type: 'extension_error',
          filtered: true
        })
      );
    });

    it('should work without context parameter', () => {
      const result = handlePotentialExtensionError('runtime.lastError');
      expect(result).toBe(true);
      expect(logger.debug).toHaveBeenCalledWith(
        'Filtered browser extension error',
        expect.any(Object)
      );
    });
  });

  describe('filteredErrorHandler', () => {
    let preventDefaultSpy: ReturnType<typeof vi.fn>;
    let errorEvent: ErrorEvent;

    beforeEach(() => {
      preventDefaultSpy = vi.fn();
      errorEvent = {
        message: 'Test error',
        filename: 'test.js',
        lineno: 10,
        colno: 5,
        error: new Error('Test error'),
        preventDefault: preventDefaultSpy
      } as ErrorEvent;
    });

    it('should filter extension errors and prevent default', () => {
      errorEvent.message = 'runtime.lastError occurred';
      
      filteredErrorHandler(errorEvent);
      
      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalled();
      expect(logger.error).not.toHaveBeenCalled();
    });

    it('should handle non-extension errors normally', () => {
      errorEvent.message = 'Application error';
      
      filteredErrorHandler(errorEvent);
      
      expect(preventDefaultSpy).not.toHaveBeenCalled();
      expect(logger.debug).not.toHaveBeenCalled();
      expect(logger.error).toHaveBeenCalledWith('Application error', expect.objectContaining({
        message: 'Application error',
        filename: 'test.js',
        lineno: 10,
        colno: 5
      }));
    });

    it('should use fallback handler for non-extension errors', () => {
      const fallbackHandler = vi.fn();
      errorEvent.message = 'Application error';
      
      filteredErrorHandler(errorEvent, fallbackHandler);
      
      expect(fallbackHandler).toHaveBeenCalledWith(errorEvent);
      expect(logger.error).not.toHaveBeenCalled();
    });

    it('should not use fallback handler for extension errors', () => {
      const fallbackHandler = vi.fn();
      errorEvent.message = 'Extension context invalidated';
      
      filteredErrorHandler(errorEvent, fallbackHandler);
      
      expect(fallbackHandler).not.toHaveBeenCalled();
      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe('filteredRejectionHandler', () => {
    let preventDefaultSpy: ReturnType<typeof vi.fn>;
    let rejectionEvent: PromiseRejectionEvent;

    beforeEach(() => {
      preventDefaultSpy = vi.fn();
      // Create a mock promise that doesn't actually reject to avoid unhandled rejections in tests
      const mockPromise = Promise.resolve();
      rejectionEvent = {
        reason: 'Test rejection',
        promise: mockPromise,
        preventDefault: preventDefaultSpy
      } as PromiseRejectionEvent;
    });

    it('should filter extension rejection errors', () => {
      rejectionEvent.reason = 'runtime.lastError: Connection failed';
      
      filteredRejectionHandler(rejectionEvent);
      
      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalled();
      expect(logger.error).not.toHaveBeenCalled();
    });

    it('should handle non-extension rejections normally', () => {
      rejectionEvent.reason = 'Network request failed';
      
      filteredRejectionHandler(rejectionEvent);
      
      expect(preventDefaultSpy).not.toHaveBeenCalled();
      expect(logger.debug).not.toHaveBeenCalled();
      expect(logger.error).toHaveBeenCalledWith('Unhandled promise rejection', {
        reason: 'Network request failed',
        type: 'unhandled_rejection'
      });
    });

    it('should use fallback handler for non-extension rejections', () => {
      const fallbackHandler = vi.fn();
      rejectionEvent.reason = 'Application rejection';
      
      filteredRejectionHandler(rejectionEvent, fallbackHandler);
      
      expect(fallbackHandler).toHaveBeenCalledWith(rejectionEvent);
      expect(logger.error).not.toHaveBeenCalled();
    });

    it('should handle Error objects as rejection reasons', () => {
      const extensionError = new Error('Extension context invalidated');
      rejectionEvent.reason = extensionError;
      
      filteredRejectionHandler(rejectionEvent);
      
      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalled();
    });
  });

  describe('setupConsoleErrorFilter', () => {
    let originalError: typeof console.error;
    let originalWarn: typeof console.warn;
    let errorSpy: ReturnType<typeof vi.fn>;
    let warnSpy: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      originalError = console.error;
      originalWarn = console.warn;
      errorSpy = vi.fn();
      warnSpy = vi.fn();
      console.error = errorSpy;
      console.warn = warnSpy;
    });

    afterEach(() => {
      console.error = originalError;
      console.warn = originalWarn;
    });

    it('should filter extension errors from console.error', () => {
      const cleanup = setupConsoleErrorFilter();
      
      console.error('runtime.lastError:', 'Connection failed');
      expect(errorSpy).not.toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalledWith('Console error filtered (extension):', {
        message: 'runtime.lastError: Connection failed',
        args: ['runtime.lastError:', 'Connection failed']
      });

      cleanup();
    });

    it('should allow non-extension errors through console.error', () => {
      const cleanup = setupConsoleErrorFilter();
      
      console.error('Application error:', 'Something went wrong');
      expect(errorSpy).toHaveBeenCalledWith('Application error:', 'Something went wrong');
      expect(logger.debug).not.toHaveBeenCalled();

      cleanup();
    });

    it('should filter extension warnings from console.warn', () => {
      const cleanup = setupConsoleErrorFilter();
      
      console.warn('chrome.runtime is not available');
      expect(warnSpy).not.toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalledWith('Console warning filtered (extension):', {
        message: 'chrome.runtime is not available',
        args: ['chrome.runtime is not available']
      });

      cleanup();
    });

    it('should allow non-extension warnings through console.warn', () => {
      const cleanup = setupConsoleErrorFilter();
      
      console.warn('Deprecation warning:', 'Feature will be removed');
      expect(warnSpy).toHaveBeenCalledWith('Deprecation warning:', 'Feature will be removed');
      
      cleanup();
    });

    it('should restore original console methods on cleanup', () => {
      const cleanup = setupConsoleErrorFilter();

      // Verify console methods were overridden
      expect(console.error).not.toBe(errorSpy);
      expect(console.warn).not.toBe(warnSpy);

      cleanup();

      // Verify console methods were restored to the spies that were there before filter
      expect(console.error).toBe(errorSpy);
      expect(console.warn).toBe(warnSpy);
    });
  });

  describe('initializeExtensionErrorFilter', () => {
    let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
    let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;
    let originalError: typeof console.error;
    let originalWarn: typeof console.warn;

    beforeEach(() => {
      addEventListenerSpy = vi.spyOn(window, 'addEventListener');
      removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');
      originalError = console.error;
      originalWarn = console.warn;
    });

    afterEach(() => {
      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
      console.error = originalError;
      console.warn = originalWarn;
    });

    it('should set up error and rejection handlers', () => {
      const cleanup = initializeExtensionErrorFilter();
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('unhandledrejection', expect.any(Function));
      expect(logger.info).toHaveBeenCalledWith('Extension error filter initialized');
      
      cleanup();
    });

    it('should handle error events through the filter', () => {
      const cleanup = initializeExtensionErrorFilter();
      
      // Get the error handler that was registered
      const errorHandler = addEventListenerSpy.mock.calls.find(
        call => call[0] === 'error'
      )?.[1] as EventListener;
      
      // Create and dispatch an extension error event
      const extensionError = new ErrorEvent('error', {
        message: 'runtime.lastError',
        filename: 'chrome-extension://abc/script.js'
      });
      
      errorHandler(extensionError);
      
      expect(logger.debug).toHaveBeenCalled();
      
      cleanup();
    });

    it('should clean up all handlers on cleanup', () => {
      const cleanup = initializeExtensionErrorFilter();
      
      // Verify console methods were overridden
      const overriddenError = console.error;
      const overriddenWarn = console.warn;
      expect(overriddenError).not.toBe(originalError);
      expect(overriddenWarn).not.toBe(originalWarn);
      
      cleanup();
      
      // Verify event listeners were removed
      expect(removeEventListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('unhandledrejection', expect.any(Function));
      
      // Verify console methods were restored
      expect(console.error).toBe(originalError);
      expect(console.warn).toBe(originalWarn);
      
      expect(logger.info).toHaveBeenCalledWith('Extension error filter cleaned up');
    });
  });
});