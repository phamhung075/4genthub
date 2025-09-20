import { describe, it, expect, vi } from 'vitest';
import { toastEventBus, ToastEvent } from '../../services/toastEventBus';

describe('ToastEventBus', () => {
  describe('Event Subscription', () => {
    it('should subscribe to events and receive them', () => {
      const mockListener = vi.fn();
      const event: ToastEvent = {
        type: 'success',
        title: 'Test Event',
        description: 'Test Description',
      };

      toastEventBus.subscribe(mockListener);
      toastEventBus.emit(event);

      expect(mockListener).toHaveBeenCalledWith(event);
      expect(mockListener).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple subscribers', () => {
      const listener1 = vi.fn();
      const listener2 = vi.fn();
      const event: ToastEvent = {
        type: 'error',
        title: 'Error Event',
      };

      toastEventBus.subscribe(listener1);
      toastEventBus.subscribe(listener2);
      toastEventBus.emit(event);

      expect(listener1).toHaveBeenCalledWith(event);
      expect(listener2).toHaveBeenCalledWith(event);
    });

    it('should unsubscribe correctly', () => {
      const listener1 = vi.fn();
      const listener2 = vi.fn();
      const event: ToastEvent = {
        type: 'info',
        title: 'Info Event',
      };

      const unsubscribe1 = toastEventBus.subscribe(listener1);
      toastEventBus.subscribe(listener2);

      // Unsubscribe first listener
      unsubscribe1();

      toastEventBus.emit(event);

      expect(listener1).not.toHaveBeenCalled();
      expect(listener2).toHaveBeenCalledWith(event);
    });

    it('should handle unsubscribe being called multiple times', () => {
      const listener = vi.fn();
      const unsubscribe = toastEventBus.subscribe(listener);

      // Call unsubscribe multiple times
      unsubscribe();
      unsubscribe();

      const event: ToastEvent = {
        type: 'warning',
        title: 'Warning Event',
      };

      toastEventBus.emit(event);

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('Convenience Methods', () => {
    it('should emit success event', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      toastEventBus.success('Success Title', 'Success Description');

      expect(listener).toHaveBeenCalledWith({
        type: 'success',
        title: 'Success Title',
        description: 'Success Description',
        action: undefined,
      });
    });

    it('should emit error event', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      toastEventBus.error('Error Title', 'Error Description');

      expect(listener).toHaveBeenCalledWith({
        type: 'error',
        title: 'Error Title',
        description: 'Error Description',
        action: undefined,
      });
    });

    it('should emit warning event', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      toastEventBus.warning('Warning Title');

      expect(listener).toHaveBeenCalledWith({
        type: 'warning',
        title: 'Warning Title',
        description: undefined,
        action: undefined,
      });
    });

    it('should emit info event', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      toastEventBus.info('Info Title', 'Info Description');

      expect(listener).toHaveBeenCalledWith({
        type: 'info',
        title: 'Info Title',
        description: 'Info Description',
        action: undefined,
      });
    });

    it('should handle events with actions', () => {
      const listener = vi.fn();
      const actionHandler = vi.fn();
      toastEventBus.subscribe(listener);

      const action = {
        label: 'Retry',
        onClick: actionHandler,
      };

      toastEventBus.error('Error Title', 'Error Description', action);

      expect(listener).toHaveBeenCalledWith({
        type: 'error',
        title: 'Error Title',
        description: 'Error Description',
        action,
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle emit with no listeners', () => {
      const event: ToastEvent = {
        type: 'success',
        title: 'No Listeners Event',
      };

      // Should not throw error
      expect(() => toastEventBus.emit(event)).not.toThrow();
    });

    it('should handle multiple events in sequence', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      toastEventBus.success('Event 1');
      toastEventBus.error('Event 2');
      toastEventBus.info('Event 3');

      expect(listener).toHaveBeenCalledTimes(3);
      expect(listener).toHaveBeenNthCalledWith(1, expect.objectContaining({ title: 'Event 1' }));
      expect(listener).toHaveBeenNthCalledWith(2, expect.objectContaining({ title: 'Event 2' }));
      expect(listener).toHaveBeenNthCalledWith(3, expect.objectContaining({ title: 'Event 3' }));
    });

    it('should maintain separate listener lists', () => {
      const listener1 = vi.fn();
      const listener2 = vi.fn();

      // Subscribe and immediately unsubscribe listener1
      const unsubscribe1 = toastEventBus.subscribe(listener1);
      unsubscribe1();

      // Subscribe listener2
      toastEventBus.subscribe(listener2);

      const event: ToastEvent = {
        type: 'info',
        title: 'Test Event',
      };

      toastEventBus.emit(event);

      expect(listener1).not.toHaveBeenCalled();
      expect(listener2).toHaveBeenCalledWith(event);
    });
  });

  describe('Event Properties', () => {
    it('should handle events with all properties', () => {
      const listener = vi.fn();
      const actionHandler = vi.fn();
      toastEventBus.subscribe(listener);

      const fullEvent: ToastEvent = {
        type: 'success',
        title: 'Complete Event',
        description: 'This event has all properties',
        action: {
          label: 'View Details',
          onClick: actionHandler,
        },
      };

      toastEventBus.emit(fullEvent);

      expect(listener).toHaveBeenCalledWith(fullEvent);
    });

    it('should handle events with minimal properties', () => {
      const listener = vi.fn();
      toastEventBus.subscribe(listener);

      const minimalEvent: ToastEvent = {
        type: 'info',
        title: 'Minimal Event',
      };

      toastEventBus.emit(minimalEvent);

      expect(listener).toHaveBeenCalledWith(minimalEvent);
    });
  });
});