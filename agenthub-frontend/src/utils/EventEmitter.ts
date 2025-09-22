/**
 * Browser-compatible EventEmitter implementation
 * Replaces Node.js 'events' module for browser use
 */

type EventHandler = (...args: any[]) => void;

export class EventEmitter {
  private events: Map<string, Set<EventHandler>> = new Map();

  on(event: string, handler: EventHandler): this {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event)!.add(handler);
    return this;
  }

  off(event: string, handler: EventHandler): this {
    const handlers = this.events.get(event);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.events.delete(event);
      }
    }
    return this;
  }

  emit(event: string, ...args: any[]): boolean {
    let hasListeners = false;

    // Emit to specific event listeners
    const handlers = this.events.get(event);
    if (handlers) {
      hasListeners = true;
      handlers.forEach(handler => {
        try {
          handler(...args);
        } catch (error) {
          console.error(`Error in event handler for "${event}":`, error);
        }
      });
    }

    // Emit to wildcard listeners
    const wildcardHandlers = this.events.get('*');
    if (wildcardHandlers) {
      hasListeners = true;
      wildcardHandlers.forEach(handler => {
        try {
          handler(...args);
        } catch (error) {
          console.error(`Error in wildcard event handler:`, error);
        }
      });
    }

    return hasListeners;
  }

  once(event: string, handler: EventHandler): this {
    const onceHandler = (...args: any[]) => {
      this.off(event, onceHandler);
      handler(...args);
    };
    return this.on(event, onceHandler);
  }

  removeAllListeners(event?: string): this {
    if (event) {
      this.events.delete(event);
    } else {
      this.events.clear();
    }
    return this;
  }

  listenerCount(event: string): number {
    const handlers = this.events.get(event);
    return handlers ? handlers.size : 0;
  }
}