/**
 * Browser Extension Error Filter
 *
 * This utility filters out browser extension-related errors that are not
 * part of our application but appear in the console due to browser extension
 * conflicts or communication failures.
 */

import logger from './logger';

// Common browser extension error patterns
const EXTENSION_ERROR_PATTERNS = [
  /runtime\.lastError/i,
  /Could not establish connection\. Receiving end does not exist/i,
  /Extension context invalidated/i,
  /chrome-extension:/i,
  /moz-extension:/i,
  /safari-extension:/i,
  /The message port closed before a response was received/i,
  /Cannot access a chrome:\/\/ URL/i,
  /Cannot access chrome:\/\//i,
  /Uncaught Error: Extension context invalidated/i,
  /chrome\.runtime is not available/i,
  /browser\.runtime is not available/i
];

// Extension script sources that should be filtered
const EXTENSION_SCRIPT_PATTERNS = [
  /chrome-extension:\/\//i,
  /moz-extension:\/\//i,
  /safari-extension:\/\//i,
  /extension\//i
];

/**
 * Check if an error is likely from a browser extension
 */
export function isExtensionError(error: Error | ErrorEvent | string): boolean {
  let errorMessage = '';
  let errorSource = '';

  if (typeof error === 'string') {
    errorMessage = error;
  } else if (error instanceof Error) {
    errorMessage = error.message;
    errorSource = error.stack || '';
  } else if (typeof error === 'object' && error !== null && 'message' in error) {
    errorMessage = (error as ErrorEvent).message;
    errorSource = (error as ErrorEvent).filename || '';
  }

  // Check error message patterns
  const hasExtensionPattern = EXTENSION_ERROR_PATTERNS.some(pattern =>
    pattern.test(errorMessage)
  );

  // Check if error comes from extension script
  const hasExtensionSource = EXTENSION_SCRIPT_PATTERNS.some(pattern =>
    pattern.test(errorSource)
  );

  return hasExtensionPattern || hasExtensionSource;
}

/**
 * Filter and handle extension errors appropriately
 */
export function handlePotentialExtensionError(
  error: Error | ErrorEvent | string,
  context?: string
): boolean {
  if (isExtensionError(error)) {
    // Log for debugging purposes but don't treat as application error
    logger.debug(
      `Filtered browser extension error${context ? ` in ${context}` : ''}`,
      {
        error: typeof error === 'string' ? error : error.message,
        source: error instanceof Error ? error.stack :
               'message' in error ? error.filename : 'unknown',
        type: 'extension_error',
        filtered: true
      }
    );
    return true; // Error was handled/filtered
  }
  return false; // Error should be processed normally
}

/**
 * Enhanced error handler that filters extension errors
 */
export function filteredErrorHandler(
  event: ErrorEvent,
  fallbackHandler?: (event: ErrorEvent) => void
): void {
  if (handlePotentialExtensionError(event, 'global error handler')) {
    // Extension error was filtered, prevent default handling
    event.preventDefault();
    return;
  }

  // Not an extension error, use fallback handler or default behavior
  if (fallbackHandler) {
    fallbackHandler(event);
  } else {
    // Log application errors normally
    logger.error('Application error', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error
    });
  }
}

/**
 * Enhanced unhandled rejection handler that filters extension errors
 */
export function filteredRejectionHandler(
  event: PromiseRejectionEvent,
  fallbackHandler?: (event: PromiseRejectionEvent) => void
): void {
  const error = event.reason;

  if (handlePotentialExtensionError(error, 'unhandled promise rejection')) {
    // Extension error was filtered, prevent default handling
    event.preventDefault();
    return;
  }

  // Not an extension error, use fallback handler or default behavior
  if (fallbackHandler) {
    fallbackHandler(event);
  } else {
    // Log application rejections normally
    logger.error('Unhandled promise rejection', {
      reason: error,
      type: 'unhandled_rejection'
    });
  }
}

/**
 * Console error interceptor that filters extension errors
 */
export function setupConsoleErrorFilter(): () => void {
  const originalError = console.error;
  const originalWarn = console.warn;

  // Override console.error to filter extension errors
  console.error = (...args: any[]) => {
    const message = args.join(' ');
    if (isExtensionError(message)) {
      // Log as debug instead of error for extension issues
      logger.debug('Console error filtered (extension):', { message, args });
      return;
    }
    // Call original console.error for non-extension errors
    originalError.apply(console, args);
  };

  // Override console.warn for extension warnings
  console.warn = (...args: any[]) => {
    const message = args.join(' ');
    if (isExtensionError(message)) {
      // Log as debug instead of warning for extension issues
      logger.debug('Console warning filtered (extension):', { message, args });
      return;
    }
    // Call original console.warn for non-extension warnings
    originalWarn.apply(console, args);
  };

  // Return cleanup function
  return () => {
    console.error = originalError;
    console.warn = originalWarn;
  };
}

/**
 * Initialize extension error filtering
 */
export function initializeExtensionErrorFilter(): () => void {
  const cleanupFunctions: Array<() => void> = [];

  // Set up global error handlers
  const handleError = (event: ErrorEvent) => {
    filteredErrorHandler(event);
  };

  const handleRejection = (event: PromiseRejectionEvent) => {
    filteredRejectionHandler(event);
  };

  // Add event listeners
  window.addEventListener('error', handleError);
  window.addEventListener('unhandledrejection', handleRejection);

  // Set up console filtering
  const cleanupConsole = setupConsoleErrorFilter();
  cleanupFunctions.push(cleanupConsole);

  // Add cleanup for event listeners
  cleanupFunctions.push(() => {
    window.removeEventListener('error', handleError);
    window.removeEventListener('unhandledrejection', handleRejection);
  });

  logger.info('Extension error filter initialized');

  // Return master cleanup function
  return () => {
    cleanupFunctions.forEach(cleanup => cleanup());
    logger.info('Extension error filter cleaned up');
  };
}