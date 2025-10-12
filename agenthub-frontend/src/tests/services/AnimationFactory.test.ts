/**
 * Unit tests for AnimationFactory - Centralized Animation Management System
 * Tests CSS class application, animation timing, coordination logic, and priority system.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import animationFactory from '../../services/AnimationFactory';

// Mock DOM elements
const createMockElement = () => {
  const element = {
    tagName: 'DIV',
    classList: {
      add: vi.fn(),
      remove: vi.fn(),
      contains: vi.fn().mockReturnValue(false)
    },
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  } as any;
  return element;
};

describe('AnimationFactory', () => {
  let mockElement: HTMLElement;
  let mockCallbacks: {
    onAnimationStart: ReturnType<typeof vi.fn>;
    onAnimationEnd: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    // Clear all existing registrations from the singleton instance
    // We can't access private properties directly, so we'll unregister test elements in afterEach
    mockElement = createMockElement();
    mockCallbacks = {
      onAnimationStart: vi.fn(),
      onAnimationEnd: vi.fn()
    };

    // Mock timers
    vi.useFakeTimers();

    // Mock console methods to reduce noise in tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    // Clean up test elements
    animationFactory.unregisterElement('test-element');
    animationFactory.unregisterElement('test-task');
    animationFactory.unregisterElement('task-1');
    animationFactory.unregisterElement('task-2');
    animationFactory.unregisterElement('task-3');
    animationFactory.unregisterElement('unregistered-element');

    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('Element Registration', () => {
    it('should register element successfully', () => {
      const elementId = 'test-element';

      animationFactory.registerElement(elementId, mockElement, mockCallbacks);

      // Should not throw and element should be registered
      expect(() => {
        animationFactory.animate(elementId, 'create');
      }).not.toThrow();
    });

    it('should unregister element and clean up state', () => {
      const elementId = 'test-element';

      // Register element
      animationFactory.registerElement(elementId, mockElement);

      // Start animation to create state
      animationFactory.animate(elementId, 'create');

      // Unregister element
      animationFactory.unregisterElement(elementId);

      // Should return false when trying to animate unregistered element
      const result = animationFactory.animate(elementId, 'update');
      expect(result).toBe(false);
    });

    it('should handle registration with partial callbacks', () => {
      const elementId = 'test-element';
      const partialCallbacks = {
        onAnimationStart: mockCallbacks.onAnimationStart
        // onAnimationEnd intentionally missing
      };

      animationFactory.registerElement(elementId, mockElement, partialCallbacks);

      const result = animationFactory.animate(elementId, 'create');
      expect(result).toBe(true);
      expect(mockCallbacks.onAnimationStart).toHaveBeenCalledWith('create');
    });
  });

  describe('CSS Class Application', () => {
    beforeEach(() => {
      animationFactory.registerElement('test-task', mockElement, mockCallbacks);
    });

    it('should apply correct CSS class for CREATE animation', () => {
      const result = animationFactory.animate('test-task', 'create');

      expect(result).toBe(true);
      expect(mockElement.classList.add).toHaveBeenCalledWith('draw-in-left-to-right');
    });

    it('should apply correct CSS class for UPDATE animation', () => {
      const result = animationFactory.animate('test-task', 'update');

      expect(result).toBe(true);
      expect(mockElement.classList.add).toHaveBeenCalledWith('content-update');
    });

    it('should apply correct CSS class for DELETE animation', () => {
      const result = animationFactory.animate('test-task', 'delete');

      expect(result).toBe(true);
      expect(mockElement.classList.add).toHaveBeenCalledWith('fade-out-left-to-right');
    });

    it('should apply correct CSS class for COMPLETE animation', () => {
      const result = animationFactory.animate('test-task', 'complete');

      expect(result).toBe(true);
      expect(mockElement.classList.add).toHaveBeenCalledWith('task-celebration');
    });

    it('should remove existing animation classes before adding new ones', () => {
      // First animation
      animationFactory.animate('test-task', 'create');

      // Clear mock calls
      mockElement.classList.remove.mockClear();

      // Second animation
      animationFactory.animate('test-task', 'update');

      // Should remove all existing animation classes
      expect(mockElement.classList.remove).toHaveBeenCalledWith('draw-in-left-to-right');
      expect(mockElement.classList.remove).toHaveBeenCalledWith('fade-out-left-to-right');
      expect(mockElement.classList.remove).toHaveBeenCalledWith('content-update');
      expect(mockElement.classList.remove).toHaveBeenCalledWith('task-celebration');
    });
  });

  describe('Animation Durations', () => {
    beforeEach(() => {
      animationFactory.registerElement('test-task', mockElement, mockCallbacks);
    });

    it('should have correct duration for CREATE animation (500ms)', () => {
      animationFactory.animate('test-task', 'create');

      // Fast forward to just before cleanup time
      vi.advanceTimersByTime(499);
      expect(mockElement.classList.remove).not.toHaveBeenCalled();

      // Fast forward to cleanup time
      vi.advanceTimersByTime(1);
      expect(mockElement.classList.remove).toHaveBeenCalledWith('draw-in-left-to-right');
    });

    it('should have correct duration for DELETE animation (800ms)', () => {
      animationFactory.animate('test-task', 'delete');

      // Fast forward to just before cleanup time
      vi.advanceTimersByTime(799);
      expect(mockElement.classList.remove).not.toHaveBeenCalled();

      // Fast forward to cleanup time
      vi.advanceTimersByTime(1);
      expect(mockElement.classList.remove).toHaveBeenCalledWith('fade-out-left-to-right');
    });

    it('should have correct duration for UPDATE animation (1200ms)', () => {
      animationFactory.animate('test-task', 'update');

      // Fast forward to just before cleanup time
      vi.advanceTimersByTime(1199);
      expect(mockElement.classList.remove).not.toHaveBeenCalled();

      // Fast forward to cleanup time
      vi.advanceTimersByTime(1);
      expect(mockElement.classList.remove).toHaveBeenCalledWith('content-update');
    });

    it('should have correct duration for COMPLETE animation (3000ms)', () => {
      animationFactory.animate('test-task', 'complete');

      // Fast forward to just before cleanup time
      vi.advanceTimersByTime(2999);
      expect(mockElement.classList.remove).not.toHaveBeenCalled();

      // Fast forward to cleanup time
      vi.advanceTimersByTime(1);
      expect(mockElement.classList.remove).toHaveBeenCalledWith('task-celebration');
    });
  });

  describe('Animation Coordination and Cooldown', () => {
    beforeEach(() => {
      animationFactory.registerElement('test-task', mockElement, mockCallbacks);
    });

    it('should prevent double-triggering within cooldown period', () => {
      // First animation
      const result1 = animationFactory.animate('test-task', 'create', 'callback');
      expect(result1).toBe(true);

      // Second animation within cooldown (100ms)
      vi.advanceTimersByTime(50);
      const result2 = animationFactory.animate('test-task', 'update', 'callback');
      expect(result2).toBe(false);

      // Verify only first animation was applied
      expect(mockElement.classList.add).toHaveBeenCalledTimes(1);
      expect(mockElement.classList.add).toHaveBeenCalledWith('draw-in-left-to-right');
    });

    it('should allow animation after cooldown period', () => {
      // First animation
      animationFactory.animate('test-task', 'create', 'callback');

      // Wait for cooldown to pass
      vi.advanceTimersByTime(150); // More than 100ms cooldown

      // Second animation should be allowed
      const result = animationFactory.animate('test-task', 'update', 'callback');
      expect(result).toBe(true);
    });

    it('should allow mount animations to override cooldown', () => {
      // Start with callback animation
      animationFactory.animate('test-task', 'create', 'callback');

      // Mount animation should override even within cooldown
      vi.advanceTimersByTime(50); // Within cooldown
      const result = animationFactory.animate('test-task', 'update', 'mount');
      expect(result).toBe(true);
    });

    it('should allow websocket animations to override callback animations', () => {
      // Start with callback animation
      animationFactory.animate('test-task', 'create', 'callback');

      // WebSocket animation should override callback within cooldown
      vi.advanceTimersByTime(50); // Within cooldown
      const result = animationFactory.animate('test-task', 'update', 'websocket');
      expect(result).toBe(true);
    });

    it('should not allow callback to override websocket animations', () => {
      // Start with websocket animation
      animationFactory.animate('test-task', 'create', 'websocket');

      // Callback animation should not override websocket
      vi.advanceTimersByTime(50); // Within cooldown
      const result = animationFactory.animate('test-task', 'update', 'callback');
      expect(result).toBe(false);
    });
  });

  describe('Priority System', () => {
    beforeEach(() => {
      animationFactory.registerElement('test-task', mockElement, mockCallbacks);
    });

    it('should enforce priority order: mount > websocket > callback', () => {
      // Start with callback
      const callback = animationFactory.animate('test-task', 'create', 'callback');
      expect(callback).toBe(true);

      vi.advanceTimersByTime(50); // Within cooldown

      // WebSocket should override callback
      const websocket = animationFactory.animate('test-task', 'update', 'websocket');
      expect(websocket).toBe(true);

      vi.advanceTimersByTime(50); // Within cooldown

      // Mount should override websocket
      const mount = animationFactory.animate('test-task', 'delete', 'mount');
      expect(mount).toBe(true);
    });

    it('should not allow lower priority to override higher priority', () => {
      // Start with mount animation (highest priority)
      animationFactory.animate('test-task', 'create', 'mount');

      vi.advanceTimersByTime(50); // Within cooldown

      // WebSocket should not override mount
      const websocket = animationFactory.animate('test-task', 'update', 'websocket');
      expect(websocket).toBe(false);

      // Callback should not override mount
      const callback = animationFactory.animate('test-task', 'delete', 'callback');
      expect(callback).toBe(false);
    });
  });

  describe('Animation Cleanup', () => {
    beforeEach(() => {
      animationFactory.registerElement('test-task', mockElement, mockCallbacks);
    });

    it('should clean up CSS classes after animation completes', () => {
      animationFactory.animate('test-task', 'create');

      // Fast forward to cleanup time
      vi.advanceTimersByTime(500);

      expect(mockElement.classList.remove).toHaveBeenCalledWith('draw-in-left-to-right');
    });

    it('should call onAnimationEnd callback after cleanup', () => {
      animationFactory.animate('test-task', 'create');

      // Fast forward to cleanup time
      vi.advanceTimersByTime(500);

      expect(mockCallbacks.onAnimationEnd).toHaveBeenCalledWith('create');
    });

    it('should clean up animation state after completion', () => {
      animationFactory.animate('test-task', 'create');

      // Animation should be blocked within cooldown
      vi.advanceTimersByTime(50);
      expect(animationFactory.animate('test-task', 'update', 'callback')).toBe(false);

      // After cleanup, new animations should be allowed
      vi.advanceTimersByTime(500);
      expect(animationFactory.animate('test-task', 'update', 'callback')).toBe(true);
    });

    it('should handle cleanup with missing callbacks gracefully', () => {
      // Register without callbacks
      animationFactory.unregisterElement('test-task');
      animationFactory.registerElement('test-task', mockElement);

      animationFactory.animate('test-task', 'create');

      // Should not throw when cleaning up without callbacks
      expect(() => {
        vi.advanceTimersByTime(500);
      }).not.toThrow();
    });
  });

  describe('Error Handling', () => {
    it('should return false for unregistered elements', () => {
      const result = animationFactory.animate('unregistered-element', 'create');
      expect(result).toBe(false);
    });

    it('should handle missing element gracefully', () => {
      animationFactory.registerElement('test-task', null as any);

      const result = animationFactory.animate('test-task', 'create');
      expect(result).toBe(false);
    });

    it('should handle invalid animation types gracefully', () => {
      animationFactory.registerElement('test-task', mockElement);

      const result = animationFactory.animate('test-task', 'invalid' as any);
      expect(result).toBe(false);
    });
  });

  describe('Multiple Element Support', () => {
    it('should handle multiple elements simultaneously', () => {
      const element1 = createMockElement();
      const element2 = createMockElement();
      const element3 = createMockElement();

      animationFactory.registerElement('task-1', element1);
      animationFactory.registerElement('task-2', element2);
      animationFactory.registerElement('task-3', element3);

      // Animate all elements
      const result1 = animationFactory.animate('task-1', 'create');
      const result2 = animationFactory.animate('task-2', 'update');
      const result3 = animationFactory.animate('task-3', 'delete');

      expect(result1).toBe(true);
      expect(result2).toBe(true);
      expect(result3).toBe(true);

      // Verify correct classes applied
      expect(element1.classList.add).toHaveBeenCalledWith('draw-in-left-to-right');
      expect(element2.classList.add).toHaveBeenCalledWith('content-update');
      expect(element3.classList.add).toHaveBeenCalledWith('fade-out-left-to-right');
    });

    it('should maintain independent cooldowns for different elements', () => {
      const element1 = createMockElement();
      const element2 = createMockElement();

      animationFactory.registerElement('task-1', element1);
      animationFactory.registerElement('task-2', element2);

      // Start animations on both elements
      animationFactory.animate('task-1', 'create', 'callback');
      animationFactory.animate('task-2', 'create', 'callback');

      vi.advanceTimersByTime(50); // Within cooldown

      // Both should be blocked by their own cooldowns
      expect(animationFactory.animate('task-1', 'update', 'callback')).toBe(false);
      expect(animationFactory.animate('task-2', 'update', 'callback')).toBe(false);

      // But they should not interfere with each other after cooldown
      vi.advanceTimersByTime(100); // Past cooldown

      expect(animationFactory.animate('task-1', 'update', 'callback')).toBe(true);
      expect(animationFactory.animate('task-2', 'update', 'callback')).toBe(true);
    });
  });

  describe('Debug Information', () => {
    it('should provide useful debug information', () => {
      animationFactory.registerElement('task-1', mockElement);
      animationFactory.registerElement('task-2', createMockElement());

      animationFactory.animate('task-1', 'create');

      // Debug info would be accessed through console logs in actual implementation
      // Here we verify the animations are tracked properly
      expect(animationFactory.animate('task-1', 'update', 'callback')).toBe(false); // Blocked by cooldown
      expect(animationFactory.animate('task-2', 'update', 'callback')).toBe(true);  // Different element, allowed
    });
  });
});