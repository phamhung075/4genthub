// Request Deduplication Utility
// Prevents multiple identical API calls from being made simultaneously

import logger from './logger';

interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
  callers: string[];
}

// Global map to track pending requests
const pendingRequests = new Map<string, PendingRequest>();

// Configuration
const DEDUPLICATION_TIMEOUT = 500; // 500ms window for deduplication

/**
 * Generate a unique key for a request based on URL and method
 */
function generateRequestKey(url: string, method: string = 'GET', body?: any): string {
  const bodyHash = body ? JSON.stringify(body) : '';
  return `${method}:${url}:${bodyHash}`;
}

/**
 * Get caller information for debugging
 */
function getCaller(): string {
  const stack = new Error().stack;
  if (!stack) return 'unknown';

  const lines = stack.split('\n');
  // Find the first line that's not from this utility
  for (let i = 3; i < Math.min(lines.length, 8); i++) {
    const line = lines[i];
    if (line && !line.includes('requestDeduplication') && !line.includes('apiV2')) {
      return line.trim().substring(0, 100);
    }
  }
  return 'unknown';
}

/**
 * Clean up expired pending requests
 */
function cleanupExpiredRequests(): void {
  const now = Date.now();
  pendingRequests.forEach((request, key) => {
    if (now - request.timestamp > DEDUPLICATION_TIMEOUT) {
      pendingRequests.delete(key);
      logger.debug(`🧹 Cleaned up expired request: ${key}`);
    }
  });
}

/**
 * Deduplicate requests - returns existing promise if request is already in flight
 */
export function deduplicateRequest<T>(
  url: string,
  method: string = 'GET',
  body?: any,
  requestExecutor?: () => Promise<T>
): Promise<T> | null {
  const key = generateRequestKey(url, method, body);
  const caller = getCaller();
  const now = Date.now();

  // Clean up expired requests
  cleanupExpiredRequests();

  // Check if request is already pending
  const existingRequest = pendingRequests.get(key);
  if (existingRequest) {
    // Use debug level since deduplication is expected behavior with React.StrictMode
    logger.debug(`🔄 Deduplicating request from ${caller} (expected with React.StrictMode)`, {
      url,
      method,
      key,
      existingCallers: existingRequest.callers,
      newCaller: caller,
      timeSinceOriginal: now - existingRequest.timestamp
    });

    // Add this caller to the list
    existingRequest.callers.push(caller);

    return existingRequest.promise;
  }

  // No existing request, check if we have a request executor
  if (!requestExecutor) {
    return null; // Caller should execute the request
  }

  // Execute the request and store it
  logger.debug(`🚀 Starting new request: ${key}`, { url, method, caller });

  const promise = requestExecutor()
    .then((result) => {
      // Remove from pending requests on success
      pendingRequests.delete(key);
      logger.debug(`✅ Request completed: ${key}`);
      return result;
    })
    .catch((error) => {
      // Remove from pending requests on error
      pendingRequests.delete(key);
      logger.debug(`❌ Request failed: ${key}`, error);
      throw error;
    });

  // Store the pending request
  pendingRequests.set(key, {
    promise,
    timestamp: now,
    callers: [caller]
  });

  return promise;
}

/**
 * Check if a request is currently pending
 */
export function isRequestPending(url: string, method: string = 'GET', body?: any): boolean {
  const key = generateRequestKey(url, method, body);
  const request = pendingRequests.get(key);

  if (!request) return false;

  const now = Date.now();
  if (now - request.timestamp > DEDUPLICATION_TIMEOUT) {
    pendingRequests.delete(key);
    return false;
  }

  return true;
}

/**
 * Get statistics about pending requests (for debugging)
 */
export function getDeduplicationStats(): {
  pendingCount: number;
  pendingRequests: Array<{
    key: string;
    timestamp: number;
    age: number;
    callers: string[];
  }>;
} {
  const now = Date.now();
  const requests = Array.from(pendingRequests.entries()).map(([key, request]) => ({
    key,
    timestamp: request.timestamp,
    age: now - request.timestamp,
    callers: request.callers
  }));

  return {
    pendingCount: pendingRequests.size,
    pendingRequests: requests
  };
}

/**
 * Clear all pending requests (for testing or reset)
 */
export function clearDeduplicationCache(): void {
  pendingRequests.clear();
  logger.debug('🧹 Cleared all request deduplication cache');
}

// Make stats available globally for debugging
declare global {
  interface Window {
    getRequestDeduplicationStats: () => any;
    clearRequestDeduplicationCache: () => void;
  }
}

if (typeof window !== 'undefined') {
  window.getRequestDeduplicationStats = getDeduplicationStats;
  window.clearRequestDeduplicationCache = clearDeduplicationCache;
}