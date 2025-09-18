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
  private listeners: Array<(event: ToastEvent) => void> = [];

  /**
   * Subscribe to toast events
   */
  subscribe(callback: (event: ToastEvent) => void): () => void {
    this.listeners.push(callback);

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  /**
   * Emit a toast event to all listeners
   */
  emit(event: ToastEvent): void {
    this.listeners.forEach(listener => listener(event));
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