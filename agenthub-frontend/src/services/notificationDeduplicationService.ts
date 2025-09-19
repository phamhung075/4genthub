/**
 * Notification Deduplication Service
 *
 * CRITICAL EMERGENCY FIX: Prevents duplicate notifications from reaching users
 * This service acts as a client-side fallback while server-side issues persist
 *
 * PROBLEM: Users experiencing 7 duplicate notifications per task update
 * SOLUTION: Time-window based deduplication with content hashing
 */

import logger from '../utils/logger';

interface NotificationSignature {
  entityType: string;
  eventType: string;
  entityId?: string;
  userId?: string;
  contentHash: string;
  timestamp: number;
}

interface DeduplicationConfig {
  windowMs: number;        // Time window for deduplication (default: 10000ms = 10 seconds)
  maxCacheSize: number;    // Maximum number of entries to keep in cache (default: 1000)
  cleanupIntervalMs: number; // How often to clean up old entries (default: 30000ms = 30 seconds)
  enabled: boolean;        // EMERGENCY: Enable/disable deduplication entirely (default: true)
}

class NotificationDeduplicationService {
  private cache = new Map<string, NotificationSignature>();
  private cleanupInterval: NodeJS.Timeout | null = null;
  private config: DeduplicationConfig;

  constructor(config?: Partial<DeduplicationConfig>) {
    this.config = {
      windowMs: 10000,           // 10 second window to catch all duplicates
      maxCacheSize: 1000,        // Reasonable memory limit
      cleanupIntervalMs: 30000,  // Clean up every 30 seconds
      enabled: true,             // EMERGENCY: Can be set to false to disable deduplication
      ...config
    };

    this.startCleanupInterval();
    logger.info('🚫 Notification deduplication service initialized', {
      windowMs: this.config.windowMs,
      maxCacheSize: this.config.maxCacheSize
    });
  }

  /**
   * Check if a notification should be shown or is a duplicate
   * Returns true if notification should be shown, false if it's a duplicate
   */
  shouldShowNotification(
    entityType: string,
    eventType: string,
    entityName?: string,
    entityId?: string,
    userId?: string,
    additionalData?: any
  ): boolean {
    // EMERGENCY BYPASS: If deduplication is disabled, always show notifications
    if (!this.config.enabled) {
      console.log('🔓 DEDUP BYPASSED: Deduplication disabled, allowing notification', {
        entityType,
        eventType,
        entityName,
        entityId
      });
      return true;
    }

    const now = Date.now();

    // EMERGENCY DEBUG: Enhanced logging to identify blocking issues
    const debugInfo = {
      entityType,
      eventType,
      entityName,
      entityId,
      userId,
      additionalData,
      timestamp: now,
      cacheSize: this.cache.size
    };

    // Create a content hash from all notification data
    const contentHash = this.createContentHash({
      entityType,
      eventType,
      entityName,
      entityId,
      userId,
      additionalData
    });

    // Create a unique key for this notification type
    const key = this.createDeduplicationKey(entityType, eventType, entityId, userId);

    // EMERGENCY DEBUG: Log all attempts
    console.log('🔍 DEDUP DEBUG: Checking notification', {
      ...debugInfo,
      key,
      contentHash,
      windowMs: this.config.windowMs
    });

    // Check if we've seen this notification recently
    const existingSignature = this.cache.get(key);

    if (existingSignature) {
      const timeDiff = now - existingSignature.timestamp;
      const isWithinWindow = timeDiff < this.config.windowMs;
      const isSameContent = existingSignature.contentHash === contentHash;

      // EMERGENCY DEBUG: Log detailed comparison
      console.log('🔍 DEDUP DEBUG: Found existing signature', {
        key,
        timeDiff,
        isWithinWindow,
        isSameContent,
        windowMs: this.config.windowMs,
        existingHash: existingSignature.contentHash,
        newHash: contentHash,
        existingTimestamp: existingSignature.timestamp,
        newTimestamp: now
      });

      // If within the time window and same content, it's a duplicate
      if (isWithinWindow && isSameContent) {
        console.warn('🚫 DEDUP BLOCKED: Duplicate notification blocked', {
          key,
          timeDiff,
          contentHash,
          entityType,
          eventType,
          entityId,
          reason: 'within_window_and_same_content'
        });
        return false; // Don't show - it's a duplicate
      } else {
        console.log('✅ DEDUP ALLOWED: Different content or outside window', {
          key,
          timeDiff,
          isWithinWindow,
          isSameContent,
          reason: isWithinWindow ? 'different_content' : 'outside_window'
        });
      }
    } else {
      console.log('✅ DEDUP ALLOWED: No existing signature found', { key });
    }

    // Not a duplicate - record this notification and allow it
    const signature: NotificationSignature = {
      entityType,
      eventType,
      entityId,
      userId,
      contentHash,
      timestamp: now
    };

    this.cache.set(key, signature);

    // Enforce cache size limit
    if (this.cache.size > this.config.maxCacheSize) {
      this.enforceMaxCacheSize();
    }

    console.log('✅ DEDUP FINAL: Notification allowed and cached', {
      key,
      contentHash,
      entityType,
      eventType,
      entityId,
      cacheSize: this.cache.size
    });

    return true; // Show the notification
  }

  /**
   * Create a deduplication key for this notification
   */
  private createDeduplicationKey(
    entityType: string,
    eventType: string,
    entityId?: string,
    userId?: string
  ): string {
    // Create a unique key that groups similar notifications
    const parts = [
      entityType,
      eventType,
      entityId || 'unknown',
      userId || 'anonymous'
    ];

    return parts.join('::');
  }

  /**
   * Create a hash of the notification content to detect exact duplicates
   */
  private createContentHash(data: any): string {
    // Simple hash function for notification content
    const content = JSON.stringify(data, Object.keys(data).sort());
    let hash = 0;

    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }

    return hash.toString(36); // Base36 for shorter string
  }

  /**
   * Clean up old entries from the cache
   */
  private cleanup(): void {
    const now = Date.now();
    const cutoff = now - this.config.windowMs;
    let removedCount = 0;

    for (const [key, signature] of this.cache.entries()) {
      if (signature.timestamp < cutoff) {
        this.cache.delete(key);
        removedCount++;
      }
    }

    if (removedCount > 0) {
      logger.debug('🧹 Notification cache cleanup', {
        removedCount,
        remainingSize: this.cache.size,
        cutoffTime: new Date(cutoff).toISOString()
      });
    }
  }

  /**
   * Enforce maximum cache size by removing oldest entries
   */
  private enforceMaxCacheSize(): void {
    if (this.cache.size <= this.config.maxCacheSize) {
      return;
    }

    // Convert to array, sort by timestamp, and remove oldest entries
    const entries = Array.from(this.cache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);

    const entriesToRemove = entries.slice(0, this.cache.size - this.config.maxCacheSize);

    for (const [key] of entriesToRemove) {
      this.cache.delete(key);
    }

    logger.debug('📏 Cache size limit enforced', {
      removedCount: entriesToRemove.length,
      newSize: this.cache.size,
      maxSize: this.config.maxCacheSize
    });
  }

  /**
   * Start the periodic cleanup interval
   */
  private startCleanupInterval(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    this.cleanupInterval = setInterval(() => {
      this.cleanup();
    }, this.config.cleanupIntervalMs);
  }

  /**
   * Stop the cleanup interval (for cleanup/testing)
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.cache.clear();
    logger.info('🗑️ Notification deduplication service destroyed');
  }

  /**
   * Get current cache stats (for debugging)
   */
  getStats(): {
    cacheSize: number;
    config: DeduplicationConfig;
    oldestEntry?: Date;
    newestEntry?: Date;
  } {
    const timestamps = Array.from(this.cache.values()).map(s => s.timestamp);

    return {
      cacheSize: this.cache.size,
      config: this.config,
      oldestEntry: timestamps.length > 0 ? new Date(Math.min(...timestamps)) : undefined,
      newestEntry: timestamps.length > 0 ? new Date(Math.max(...timestamps)) : undefined
    };
  }

  /**
   * Clear the cache (for testing or manual reset)
   */
  clearCache(): void {
    const prevSize = this.cache.size;
    this.cache.clear();
    logger.info('🔄 Notification deduplication cache cleared', {
      previousSize: prevSize
    });
  }

  /**
   * EMERGENCY: Enable or disable deduplication at runtime
   */
  setEnabled(enabled: boolean): void {
    const wasEnabled = this.config.enabled;
    this.config.enabled = enabled;
    if (enabled !== wasEnabled) {
      logger.info(`🔧 Deduplication ${enabled ? 'ENABLED' : 'DISABLED'}`, {
        wasEnabled,
        nowEnabled: enabled,
        cacheSize: this.cache.size
      });
      console.log(`🔧 DEDUP ${enabled ? 'ENABLED' : 'DISABLED'}: Deduplication ${enabled ? 'activated' : 'deactivated'}`);
    }
  }

  /**
   * Check if deduplication is currently enabled
   */
  isEnabled(): boolean {
    return this.config.enabled;
  }
}

// Export singleton instance with EMERGENCY DEBUG settings
export const notificationDeduplicationService = new NotificationDeduplicationService({
  windowMs: 2000,       // REDUCED: 2 second window for testing (was 10 seconds)
  maxCacheSize: 500,    // Reasonable limit for client-side cache
  cleanupIntervalMs: 30000,  // Clean up every 30 seconds
  enabled: true         // EMERGENCY: Can be disabled if needed
});

// EMERGENCY: Expose global testing functions for browser console debugging
if (typeof window !== 'undefined') {
  (window as any).debugDedup = {
    disable: () => notificationDeduplicationService.setEnabled(false),
    enable: () => notificationDeduplicationService.setEnabled(true),
    isEnabled: () => notificationDeduplicationService.isEnabled(),
    getStats: () => notificationDeduplicationService.getStats(),
    clearCache: () => notificationDeduplicationService.clearCache(),
    testNotification: (type = 'info', message = 'Test notification') => {
      console.log('🧪 Testing notification:', { type, message });
      import('./notificationService').then(({ notify }) => {
        notify[type](message, { duration: 5000 });
      });
    }
  };
  console.log('🔧 Debug tools available: window.debugDedup');
}

// Export the class for testing
export { NotificationDeduplicationService };

// Export types for type safety
export type { DeduplicationConfig, NotificationSignature };