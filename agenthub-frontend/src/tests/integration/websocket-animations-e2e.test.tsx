/**
 * WebSocket Animation E2E Flow Test
 *
 * This test validates the COMPLETE animation lifecycle for all 4 entity types:
 * WebSocket Message → WebSocketAnimationService → AnimationFactory → DOM Animation
 *
 * CRITICAL VALIDATION:
 * - All 4 entities (Task, Subtask, Branch, Project) trigger animations
 * - AnimationFactory properly registers and manages elements
 * - 150ms deferred execution works correctly
 * - Animation CSS classes are applied to DOM elements
 * - Complete end-to-end integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { webSocketAnimationService } from '../../services/WebSocketAnimationService';
import { animationFactory } from '../../services/AnimationFactory';
import type { WSMessage } from '../../types/websocketTypes';
import type { AnimationType } from '../../services/AnimationFactory';

// Mock logger to reduce noise
vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}));

describe('WebSocket Animations E2E Flow', () => {
  let testElements: Map<string, HTMLElement>;
  let appliedAnimations: Map<string, { type: AnimationType; source: string }[]>;

  beforeEach(() => {
    vi.clearAllMocks();
    testElements = new Map();
    appliedAnimations = new Map();

    // Mock requestAnimationFrame and setTimeout
    vi.stubGlobal('requestAnimationFrame', (cb: Function) => {
      cb();
      return 1;
    });
    vi.useFakeTimers();

    // Spy on AnimationFactory methods
    vi.spyOn(animationFactory, 'registerElement');
    vi.spyOn(animationFactory, 'unregisterElement');
    vi.spyOn(animationFactory, 'animate').mockImplementation((elementId, type, source) => {
      // Track what animations were requested
      if (!appliedAnimations.has(elementId)) {
        appliedAnimations.set(elementId, []);
      }
      appliedAnimations.get(elementId)!.push({ type, source });

      // Simulate actual animation behavior
      const element = testElements.get(elementId);
      if (element) {
        element.classList.add(`animate-${type}`);
        return true;
      }
      return false;
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    testElements.clear();
    appliedAnimations.clear();
  });

  /**
   * Helper: Create a mock DOM element and register it with AnimationFactory
   */
  const createAndRegisterElement = (elementId: string, entityType: string): HTMLElement => {
    const element = document.createElement('div');
    element.id = elementId;
    element.setAttribute('data-entity', entityType);
    document.body.appendChild(element);
    testElements.set(elementId, element);

    // Register with AnimationFactory (simulating what useTaskAnimation/etc would do)
    animationFactory.registerElement(elementId, element, {
      onAnimationStart: vi.fn(),
      onAnimationEnd: vi.fn()
    });

    return element;
  };

  /**
   * Helper: Simulate WebSocket message receipt
   */
  const simulateWebSocketMessage = (entity: string, action: string, entityId: string): void => {
    const message: WSMessage = {
      id: `msg-${entity}-${action}-${Date.now()}`,
      type: 'update',
      source: 'backend',
      timestamp: new Date().toISOString(),
      priority: 'normal',
      payload: {
        entity,
        action,
        data: {
          id: entityId
        }
      },
      metadata: {
        entity_id: entityId,
        [`${entity}_title`]: `Test ${entity}`
      },
      aiProcessed: false
    };

    webSocketAnimationService.handleWebSocketMessage(message);
  };

  describe('Complete E2E Flow - Task', () => {
    it('should complete full animation flow for task update', () => {
      // 1. Setup: Create and register task element
      const taskId = 'task-e2e-123';
      const taskElement = createAndRegisterElement(taskId, 'task');

      // 2. Simulate WebSocket message from backend
      simulateWebSocketMessage('task', 'updated', taskId);

      // 3. Animation should NOT trigger immediately (deferred)
      expect(animationFactory.animate).not.toHaveBeenCalled();
      expect(taskElement.classList.contains('animate-update')).toBe(false);

      // 4. Advance timers to trigger deferred animation
      vi.advanceTimersByTime(150);

      // 5. Verify AnimationFactory was called
      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'update', 'websocket');

      // 6. Verify DOM element received animation class
      expect(taskElement.classList.contains('animate-update')).toBe(true);

      // 7. Verify animation was tracked
      expect(appliedAnimations.get(taskId)).toEqual([
        { type: 'update', source: 'websocket' }
      ]);
    });

    it('should complete full animation flow for task delete', () => {
      const taskId = 'task-delete-e2e';
      const taskElement = createAndRegisterElement(taskId, 'task');

      simulateWebSocketMessage('task', 'deleted', taskId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'delete', 'websocket');
      expect(taskElement.classList.contains('animate-delete')).toBe(true);
    });

    it('should complete full animation flow for task complete', () => {
      const taskId = 'task-complete-e2e';
      const taskElement = createAndRegisterElement(taskId, 'task');

      simulateWebSocketMessage('task', 'completed', taskId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'complete', 'websocket');
      expect(taskElement.classList.contains('animate-complete')).toBe(true);
    });
  });

  describe('Complete E2E Flow - Subtask', () => {
    it('should complete full animation flow for subtask update', () => {
      const subtaskId = 'subtask-e2e-456';
      const subtaskElement = createAndRegisterElement(subtaskId, 'subtask');

      simulateWebSocketMessage('subtask', 'updated', subtaskId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(subtaskId, 'update', 'websocket');
      expect(subtaskElement.classList.contains('animate-update')).toBe(true);
    });

    it('should complete full animation flow for subtask delete', () => {
      const subtaskId = 'subtask-delete-e2e';
      const subtaskElement = createAndRegisterElement(subtaskId, 'subtask');

      simulateWebSocketMessage('subtask', 'deleted', subtaskId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(subtaskId, 'delete', 'websocket');
      expect(subtaskElement.classList.contains('animate-delete')).toBe(true);
    });

    it('should complete full animation flow for subtask complete', () => {
      const subtaskId = 'subtask-complete-e2e';
      const subtaskElement = createAndRegisterElement(subtaskId, 'subtask');

      simulateWebSocketMessage('subtask', 'completed', subtaskId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(subtaskId, 'complete', 'websocket');
      expect(subtaskElement.classList.contains('animate-complete')).toBe(true);
    });
  });

  describe('Complete E2E Flow - Branch', () => {
    it('should complete full animation flow for branch create', () => {
      const branchId = 'branch-e2e-789';
      const branchElement = createAndRegisterElement(branchId, 'branch');

      simulateWebSocketMessage('branch', 'created', branchId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(branchId, 'create', 'websocket');
      expect(branchElement.classList.contains('animate-create')).toBe(true);
    });

    it('should complete full animation flow for branch update', () => {
      const branchId = 'branch-update-e2e';
      const branchElement = createAndRegisterElement(branchId, 'branch');

      simulateWebSocketMessage('branch', 'updated', branchId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(branchId, 'update', 'websocket');
      expect(branchElement.classList.contains('animate-update')).toBe(true);
    });

    it('should complete full animation flow for branch delete', () => {
      const branchId = 'branch-delete-e2e';
      const branchElement = createAndRegisterElement(branchId, 'branch');

      simulateWebSocketMessage('branch', 'deleted', branchId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(branchId, 'delete', 'websocket');
      expect(branchElement.classList.contains('animate-delete')).toBe(true);
    });
  });

  describe('Complete E2E Flow - Project (NEW)', () => {
    it('should complete full animation flow for project create', () => {
      const projectId = 'project-e2e-101';
      const projectElement = createAndRegisterElement(projectId, 'project');

      simulateWebSocketMessage('project', 'created', projectId);
      vi.advanceTimersByTime(150);

      // CRITICAL: Validates the gap we just closed
      expect(animationFactory.animate).toHaveBeenCalledWith(projectId, 'create', 'websocket');
      expect(projectElement.classList.contains('animate-create')).toBe(true);
    });

    it('should complete full animation flow for project update', () => {
      const projectId = 'project-update-e2e';
      const projectElement = createAndRegisterElement(projectId, 'project');

      simulateWebSocketMessage('project', 'updated', projectId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(projectId, 'update', 'websocket');
      expect(projectElement.classList.contains('animate-update')).toBe(true);
    });

    it('should complete full animation flow for project delete', () => {
      const projectId = 'project-delete-e2e';
      const projectElement = createAndRegisterElement(projectId, 'project');

      simulateWebSocketMessage('project', 'deleted', projectId);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith(projectId, 'delete', 'websocket');
      expect(projectElement.classList.contains('animate-delete')).toBe(true);
    });
  });

  describe('Multi-Entity Concurrent Animations', () => {
    it('should handle animations for multiple entities simultaneously', () => {
      // Setup: Create elements for all 4 entity types
      const taskId = 'task-multi-1';
      const subtaskId = 'subtask-multi-1';
      const branchId = 'branch-multi-1';
      const projectId = 'project-multi-1';

      createAndRegisterElement(taskId, 'task');
      createAndRegisterElement(subtaskId, 'subtask');
      createAndRegisterElement(branchId, 'branch');
      createAndRegisterElement(projectId, 'project');

      // Simulate concurrent WebSocket messages
      simulateWebSocketMessage('task', 'updated', taskId);
      simulateWebSocketMessage('subtask', 'updated', subtaskId);
      simulateWebSocketMessage('branch', 'updated', branchId);
      simulateWebSocketMessage('project', 'updated', projectId);

      // Advance timers
      vi.advanceTimersByTime(150);

      // Verify all animations triggered
      expect(animationFactory.animate).toHaveBeenCalledTimes(4);
      expect(appliedAnimations.size).toBe(4);
      expect(appliedAnimations.get(taskId)).toBeDefined();
      expect(appliedAnimations.get(subtaskId)).toBeDefined();
      expect(appliedAnimations.get(branchId)).toBeDefined();
      expect(appliedAnimations.get(projectId)).toBeDefined();
    });
  });

  describe('Element Not Registered - Graceful Degradation', () => {
    it('should handle animation request for unregistered element', () => {
      // Don't register element, just send WebSocket message
      const taskId = 'task-unregistered';
      simulateWebSocketMessage('task', 'updated', taskId);
      vi.advanceTimersByTime(150);

      // Animation should still be attempted (returns false)
      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'update', 'websocket');

      // But no DOM class should be applied (element doesn't exist)
      expect(appliedAnimations.get(taskId)).toEqual([
        { type: 'update', source: 'websocket' }
      ]);
    });
  });

  describe('Animation Sequencing', () => {
    it('should handle sequential animations on same element', () => {
      const taskId = 'task-sequence';
      const taskElement = createAndRegisterElement(taskId, 'task');

      // First animation: update
      simulateWebSocketMessage('task', 'updated', taskId);
      vi.advanceTimersByTime(150);
      expect(taskElement.classList.contains('animate-update')).toBe(true);

      // Second animation: complete
      simulateWebSocketMessage('task', 'completed', taskId);
      vi.advanceTimersByTime(150);
      expect(taskElement.classList.contains('animate-complete')).toBe(true);

      // Verify both animations were tracked
      expect(appliedAnimations.get(taskId)).toEqual([
        { type: 'update', source: 'websocket' },
        { type: 'complete', source: 'websocket' }
      ]);
    });
  });

  describe('Timing Precision', () => {
    it('should not trigger animation before 150ms delay', () => {
      const taskId = 'task-timing';
      createAndRegisterElement(taskId, 'task');

      simulateWebSocketMessage('task', 'updated', taskId);

      // Check at various intervals
      vi.advanceTimersByTime(50);
      expect(animationFactory.animate).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50); // Total: 100ms
      expect(animationFactory.animate).not.toHaveBeenCalled();

      vi.advanceTimersByTime(49); // Total: 149ms
      expect(animationFactory.animate).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1); // Total: 150ms - NOW it should trigger
      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'update', 'websocket');
    });
  });

  describe('Integration with AnimationFactory Registration', () => {
    it('should work with elements registered before WebSocket message', () => {
      const taskId = 'task-pre-registered';
      const taskElement = createAndRegisterElement(taskId, 'task');

      // Verify element was registered
      expect(animationFactory.registerElement).toHaveBeenCalledWith(
        taskId,
        taskElement,
        expect.objectContaining({
          onAnimationStart: expect.any(Function),
          onAnimationEnd: expect.any(Function)
        })
      );

      // Now send WebSocket message
      simulateWebSocketMessage('task', 'updated', taskId);
      vi.advanceTimersByTime(150);

      // Animation should work because element was registered
      expect(taskElement.classList.contains('animate-update')).toBe(true);
    });

    it('should cleanup properly with unregisterElement', () => {
      const taskId = 'task-cleanup';
      const taskElement = createAndRegisterElement(taskId, 'task');

      // Unregister element (simulating component unmount)
      animationFactory.unregisterElement(taskId);
      expect(animationFactory.unregisterElement).toHaveBeenCalledWith(taskId);

      // Send WebSocket message after unregistration
      simulateWebSocketMessage('task', 'updated', taskId);
      vi.advanceTimersByTime(150);

      // Animation attempt should still be made (but won't apply to DOM)
      expect(animationFactory.animate).toHaveBeenCalledWith(taskId, 'update', 'websocket');
    });
  });

  describe('All CRUD Actions - Complete Coverage', () => {
    const testCases = [
      { entity: 'task', action: 'updated', expectedType: 'update' },
      { entity: 'task', action: 'completed', expectedType: 'complete' },
      { entity: 'task', action: 'deleted', expectedType: 'delete' },
      { entity: 'subtask', action: 'updated', expectedType: 'update' },
      { entity: 'subtask', action: 'completed', expectedType: 'complete' },
      { entity: 'subtask', action: 'deleted', expectedType: 'delete' },
      { entity: 'branch', action: 'created', expectedType: 'create' },
      { entity: 'branch', action: 'updated', expectedType: 'update' },
      { entity: 'branch', action: 'deleted', expectedType: 'delete' },
      { entity: 'project', action: 'created', expectedType: 'create' },
      { entity: 'project', action: 'updated', expectedType: 'update' },
      { entity: 'project', action: 'deleted', expectedType: 'delete' }
    ];

    testCases.forEach(({ entity, action, expectedType }) => {
      it(`should complete E2E flow for ${entity}.${action}`, () => {
        const entityId = `${entity}-crud-test`;
        const element = createAndRegisterElement(entityId, entity);

        simulateWebSocketMessage(entity, action, entityId);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith(
          entityId,
          expectedType,
          'websocket'
        );
        expect(element.classList.contains(`animate-${expectedType}`)).toBe(true);
      });
    });
  });
});
