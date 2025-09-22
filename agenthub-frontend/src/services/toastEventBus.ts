/**
 * Toast Event Bus for WebSocket Service
 *
 * This module provides a global event bus that allows the WebSocket service
 * to trigger toast notifications using the app's existing toast system.
 */

export type ToastEventType = 'success' | 'error' | 'warning' | 'info';

export interface ToastEvent {
  type: ToastEventType;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

class ToastEventBus {
  private listeners: Map<string, Set<Function>> = new Map();
  private recentMessages: Map<string, number> = new Map();
  private readonly DEDUPLICATION_WINDOW = 1000; // 1 second window for deduplication

  /**
   * Subscribe to toast events (legacy API - expects ToastEvent objects)
   */
  subscribe(callback: (event: ToastEvent) => void): () => void {
    console.log('📝 ToastEventBus.subscribe() called - adding legacy listener');

    // Add to legacy listeners for direct ToastEvent objects
    if (!this.listeners.has('legacy')) {
      this.listeners.set('legacy', new Set());
    }
    this.listeners.get('legacy')!.add(callback);

    const legacyCount = this.listeners.get('legacy')!.size;
    console.log(`📝 ToastEventBus: Now have ${legacyCount} legacy listeners`);

    // Return unsubscribe function
    return () => {
      console.log('📝 ToastEventBus: Unsubscribing legacy listener');
      this.listeners.get('legacy')?.delete(callback);
    };
  }

  /**
   * Subscribe to specific event types
   */
  on(type: string, callback: Function): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(type)?.delete(callback);
    };
  }

  /**
   * Create a deduplication key for a message
   */
  private createDeduplicationKey(typeOrEvent: string | ToastEvent, message?: string): string {
    if (typeof typeOrEvent === 'string') {
      return `${typeOrEvent}:${message || ''}`;
    } else {
      const event = typeOrEvent as ToastEvent;
      return `${event.type}:${event.title}:${event.description || ''}`;
    }
  }

  /**
   * Check if a message should be deduplicated
   */
  private shouldDeduplicate(key: string): boolean {
    const now = Date.now();
    const lastEmitted = this.recentMessages.get(key);

    if (lastEmitted && (now - lastEmitted) < this.DEDUPLICATION_WINDOW) {
      console.log(`🚫 ToastEventBus: DEDUPLICATING message with key "${key}" (last emitted ${now - lastEmitted}ms ago)`);
      return true;
    }

    // Update the timestamp for this message
    this.recentMessages.set(key, now);

    // Clean up old entries to prevent memory leaks
    for (const [existingKey, timestamp] of this.recentMessages.entries()) {
      if (now - timestamp > this.DEDUPLICATION_WINDOW * 2) {
        this.recentMessages.delete(existingKey);
      }
    }

    return false;
  }

  /**
   * Emit a toast event (overloaded method for both APIs)
   */
  emit(typeOrEvent: 'success' | 'error' | 'warning' | 'info' | 'dismiss' | ToastEvent, message?: string, options?: any): void {
    console.log('📡 ToastEventBus.emit() called with:', typeOrEvent, message, options);

    // Check for deduplication
    const deduplicationKey = this.createDeduplicationKey(typeOrEvent, message);
    if (this.shouldDeduplicate(deduplicationKey)) {
      return; // Skip this duplicate message
    }

    if (typeof typeOrEvent === 'string') {
      // New simplified API for NotificationService: emit(type, message, options)
      const listeners = this.listeners.get(typeOrEvent);
      console.log(`📡 ToastEventBus: String API - found ${listeners?.size || 0} listeners for type "${typeOrEvent}"`);
      if (listeners) {
        listeners.forEach(listener => (listener as Function)(message, options));
      }
    } else {
      // Legacy API for backward compatibility: emit(event)
      const event = typeOrEvent as ToastEvent;
      const legacyListeners = this.listeners.get('legacy') || new Set();
      console.log(`📡 ToastEventBus: Object API - found ${legacyListeners.size} legacy listeners for event:`, event);

      legacyListeners.forEach(listener => {
        console.log('📡 ToastEventBus: Calling legacy listener with event:', event);
        (listener as Function)(event);
      });

      // REMOVED: Dual notification to type-specific listeners
      // This was causing duplicate notifications when convenience methods like
      // toastEventBus.success() were called, as they triggered both legacy AND type-specific listeners
      // const typeListeners = this.listeners.get(event.type);
      // if (typeListeners) {
      //   console.log(`📡 ToastEventBus: Also notifying ${typeListeners.size} specific type listeners for "${event.type}"`);
      //   typeListeners.forEach(listener => (listener as Function)(event.title, {
      //     description: event.description,
      //     action: event.action
      //   }));
      // }
    }
  }

  /**
   * Convenience methods for different toast types
   */
  success(title: string, description?: string, action?: ToastEvent['action']): void {
    this.emit({ type: 'success', title, description, action });
  }

  error(title: string, description?: string, action?: ToastEvent['action']): void {
    this.emit({ type: 'error', title, description, action });
  }

  warning(title: string, description?: string, action?: ToastEvent['action']): void {
    this.emit({ type: 'warning', title, description, action });
  }

  info(title: string, description?: string, action?: ToastEvent['action']): void {
    this.emit({ type: 'info', title, description, action });
  }
}

// Export singleton instance
export const toastEventBus = new ToastEventBus();