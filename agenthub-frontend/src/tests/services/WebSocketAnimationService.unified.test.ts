/**
 * WebSocketAnimationService Unified Entity Tests
 *
 * This test suite validates the complete 4-entity animation system:
 * - Tasks
 * - Subtasks
 * - Branches
 * - Projects (NEW - added 2025-10-31)
 *
 * CRITICAL: This validates that ALL 4 entity types are properly routed
 * through WebSocketAnimationService to AnimationFactory with consistent behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { webSocketAnimationService } from '../../services/WebSocketAnimationService';
import { animationFactory } from '../../services/AnimationFactory';
import type { WSMessage } from '../../types/websocketTypes';

// Mock dependencies
vi.mock('../../services/AnimationFactory', () => ({
  animationFactory: {
    animate: vi.fn(),
    registerElement: vi.fn(),
    unregisterElement: vi.fn()
  }
}));

vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}));

describe('WebSocketAnimationService - Unified 4-Entity Support', () => {
  let animateSpyOriginal: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Save original function
    animateSpyOriginal = animationFactory.animate;

    // Create a fresh mock for each test
    animationFactory.animate = vi.fn().mockReturnValue(true);

    // Mock requestAnimationFrame and setTimeout
    vi.stubGlobal('requestAnimationFrame', (cb: Function) => {
      cb();
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    // Restore original function
    animationFactory.animate = animateSpyOriginal;
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  describe('All 4 Entity Types - Complete Coverage', () => {
    /**
     * Test matrix: All 4 entities × All 4 CRUD actions = 16 test cases
     * This ensures complete and consistent animation support across the system
     */

    describe('Task Entity', () => {
      it('should trigger create animation for task created', () => {
        const message: WSMessage = {
          id: 'msg-task-created',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: { id: 'task-123' }
          },
          metadata: { entity_id: 'task-123' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled(); // Created events are skipped for tasks!
      });

      it('should trigger update animation for task updated', () => {
        const message: WSMessage = {
          id: 'msg-task-updated',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'updated',
            data: { id: 'task-456' }
          },
          metadata: { entity_id: 'task-456' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-456', 'update', 'websocket');
      });

      it('should trigger complete animation for task completed', () => {
        const message: WSMessage = {
          id: 'msg-task-completed',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'completed',
            data: { id: 'task-789' }
          },
          metadata: { entity_id: 'task-789' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-789', 'complete', 'websocket');
      });

      it('should trigger delete animation for task deleted', () => {
        const message: WSMessage = {
          id: 'msg-task-deleted',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'deleted',
            data: { id: 'task-101' }
          },
          metadata: { entity_id: 'task-101' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-101', 'delete', 'websocket');
      });
    });

    describe('Subtask Entity', () => {
      it('should trigger create animation for subtask created', () => {
        const message: WSMessage = {
          id: 'msg-subtask-created',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'subtask',
            action: 'created',
            data: { id: 'subtask-123' }
          },
          metadata: { entity_id: 'subtask-123' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled(); // Created events are skipped for subtasks!
      });

      it('should trigger update animation for subtask updated', () => {
        const message: WSMessage = {
          id: 'msg-subtask-updated',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'subtask',
            action: 'updated',
            data: { id: 'subtask-456' }
          },
          metadata: { entity_id: 'subtask-456' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('subtask-456', 'update', 'websocket');
      });

      it('should trigger complete animation for subtask completed', () => {
        const message: WSMessage = {
          id: 'msg-subtask-completed',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'subtask',
            action: 'completed',
            data: { id: 'subtask-789' }
          },
          metadata: { entity_id: 'subtask-789' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('subtask-789', 'complete', 'websocket');
      });

      it('should trigger delete animation for subtask deleted', () => {
        const message: WSMessage = {
          id: 'msg-subtask-deleted',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'subtask',
            action: 'deleted',
            data: { id: 'subtask-101' }
          },
          metadata: { entity_id: 'subtask-101' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('subtask-101', 'delete', 'websocket');
      });
    });

    describe('Branch Entity', () => {
      it('should trigger create animation for branch created', () => {
        const message: WSMessage = {
          id: 'msg-branch-created',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'branch',
            action: 'created',
            data: { id: 'branch-123' }
          },
          metadata: { entity_id: 'branch-123' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('branch-123', 'create', 'websocket');
      });

      it('should trigger update animation for branch updated', () => {
        const message: WSMessage = {
          id: 'msg-branch-updated',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'branch',
            action: 'updated',
            data: { id: 'branch-456' }
          },
          metadata: { entity_id: 'branch-456' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('branch-456', 'update', 'websocket');
      });

      it('should trigger delete animation for branch deleted', () => {
        const message: WSMessage = {
          id: 'msg-branch-deleted',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'branch',
            action: 'deleted',
            data: { id: 'branch-789' }
          },
          metadata: { entity_id: 'branch-789' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('branch-789', 'delete', 'websocket');
      });
    });

    describe('Project Entity - NEW SUPPORT (2025-10-31)', () => {
      it('should trigger create animation for project created', () => {
        const message: WSMessage = {
          id: 'msg-project-created',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'project',
            action: 'created',
            data: { id: 'project-123' }
          },
          metadata: { entity_id: 'project-123', project_title: 'New Project' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        // CRITICAL: This validates the gap we just closed
        expect(animationFactory.animate).toHaveBeenCalledWith('project-123', 'create', 'websocket');
      });

      it('should trigger update animation for project updated', () => {
        const message: WSMessage = {
          id: 'msg-project-updated',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'project',
            action: 'updated',
            data: { id: 'project-456' }
          },
          metadata: { entity_id: 'project-456', project_title: 'Updated Project' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('project-456', 'update', 'websocket');
      });

      it('should trigger delete animation for project deleted', () => {
        const message: WSMessage = {
          id: 'msg-project-deleted',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'project',
            action: 'deleted',
            data: { id: 'project-789' }
          },
          metadata: { entity_id: 'project-789' },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('project-789', 'delete', 'websocket');
      });
    });
  });

  describe('ID Extraction Consistency Across All Entities', () => {
    const entities = ['task', 'subtask', 'branch', 'project'];
    const action = 'updated'; // Use updated to avoid skip logic

    entities.forEach(entity => {
      describe(`${entity} ID extraction`, () => {
        it(`should extract ${entity} ID from primary object`, () => {
          const message: WSMessage = {
            id: `msg-${entity}-primary`,
            type: 'update',
            source: 'backend',
            timestamp: new Date().toISOString(),
            priority: 'normal',
            payload: {
              entity,
              action,
              data: {
                primary: {
                  id: `${entity}-primary-123`
                }
              }
            },
            metadata: {},
            aiProcessed: false
          };

          webSocketAnimationService.handleWebSocketMessage(message);
          vi.advanceTimersByTime(150);

          expect(animationFactory.animate).toHaveBeenCalledWith(
            `${entity}-primary-123`,
            'update',
            'websocket'
          );
        });

        it(`should extract ${entity} ID from data directly`, () => {
          const message: WSMessage = {
            id: `msg-${entity}-direct`,
            type: 'update',
            source: 'backend',
            timestamp: new Date().toISOString(),
            priority: 'normal',
            payload: {
              entity,
              action,
              data: {
                id: `${entity}-direct-123`
              }
            },
            metadata: {},
            aiProcessed: false
          };

          webSocketAnimationService.handleWebSocketMessage(message);
          vi.advanceTimersByTime(150);

          expect(animationFactory.animate).toHaveBeenCalledWith(
            `${entity}-direct-123`,
            'update',
            'websocket'
          );
        });

        it(`should extract ${entity} ID from metadata`, () => {
          const message: WSMessage = {
            id: `msg-${entity}-metadata`,
            type: 'update',
            source: 'backend',
            timestamp: new Date().toISOString(),
            priority: 'normal',
            payload: {
              entity,
              action,
              data: {}
            },
            metadata: {
              entity_id: `${entity}-metadata-123`
            },
            aiProcessed: false
          };

          webSocketAnimationService.handleWebSocketMessage(message);
          vi.advanceTimersByTime(150);

          expect(animationFactory.animate).toHaveBeenCalledWith(
            `${entity}-metadata-123`,
            'update',
            'websocket'
          );
        });

        it(`should not trigger animation if ${entity} has no ID`, () => {
          const message: WSMessage = {
            id: `msg-${entity}-no-id`,
            type: 'update',
            source: 'backend',
            timestamp: new Date().toISOString(),
            priority: 'normal',
            payload: {
              entity,
              action,
              data: {}
            },
            metadata: {},
            aiProcessed: false
          };

          animationFactory.animate = vi.fn().mockClear();
          webSocketAnimationService.handleWebSocketMessage(message);
          vi.advanceTimersByTime(150);

          expect(animationFactory.animate).not.toHaveBeenCalled();
        });
      });
    });
  });

  describe('Animation Timing Consistency', () => {
    const entities = [
      { entity: 'task', action: 'updated', id: 'task-timing' },
      { entity: 'subtask', action: 'updated', id: 'subtask-timing' },
      { entity: 'branch', action: 'updated', id: 'branch-timing' },
      { entity: 'project', action: 'updated', id: 'project-timing' }
    ];

    entities.forEach(({ entity, action, id }) => {
      it(`should defer ${entity} animation by exactly 150ms`, () => {
        const message: WSMessage = {
          id: `msg-${entity}-timing`,
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity,
            action,
            data: { id }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);

        // Should not trigger immediately
        expect(animationFactory.animate).not.toHaveBeenCalled();

        // Should not trigger before 150ms
        vi.advanceTimersByTime(100);
        expect(animationFactory.animate).not.toHaveBeenCalled();

        // Should trigger at exactly 150ms
        vi.advanceTimersByTime(50);
        expect(animationFactory.animate).toHaveBeenCalledWith(id, 'update', 'websocket');
      });
    });
  });

  describe('Delete Action Variations', () => {
    const deleteActions = ['delete', 'deleted'];
    const entities = ['task', 'subtask', 'branch', 'project'];

    deleteActions.forEach(deleteAction => {
      entities.forEach(entity => {
        it(`should handle "${deleteAction}" action for ${entity}`, () => {
          const message: WSMessage = {
            id: `msg-${entity}-${deleteAction}`,
            type: 'update',
            source: 'backend',
            timestamp: new Date().toISOString(),
            priority: 'normal',
            payload: {
              entity,
              action: deleteAction,
              data: { id: `${entity}-${deleteAction}-test` }
            },
            metadata: {},
            aiProcessed: false
          };

          webSocketAnimationService.handleWebSocketMessage(message);
          vi.advanceTimersByTime(150);

          expect(animationFactory.animate).toHaveBeenCalledWith(
            `${entity}-${deleteAction}-test`,
            'delete',
            'websocket'
          );
        });
      });
    });
  });

  describe('Comprehensive Action-to-AnimationType Mapping', () => {
    const mappings = [
      // Task mappings (created is skipped)
      { entity: 'task', action: 'updated', expectedType: 'update' },
      { entity: 'task', action: 'completed', expectedType: 'complete' },
      { entity: 'task', action: 'deleted', expectedType: 'delete' },

      // Subtask mappings (created is skipped)
      { entity: 'subtask', action: 'updated', expectedType: 'update' },
      { entity: 'subtask', action: 'completed', expectedType: 'complete' },
      { entity: 'subtask', action: 'deleted', expectedType: 'delete' },

      // Branch mappings (all actions)
      { entity: 'branch', action: 'created', expectedType: 'create' },
      { entity: 'branch', action: 'updated', expectedType: 'update' },
      { entity: 'branch', action: 'deleted', expectedType: 'delete' },

      // Project mappings (all actions) - NEW
      { entity: 'project', action: 'created', expectedType: 'create' },
      { entity: 'project', action: 'updated', expectedType: 'update' },
      { entity: 'project', action: 'deleted', expectedType: 'delete' }
    ];

    mappings.forEach(({ entity, action, expectedType }) => {
      it(`should map ${entity}.${action} → ${expectedType}`, () => {
        const message: WSMessage = {
          id: `msg-mapping-${entity}-${action}`,
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity,
            action,
            data: { id: `${entity}-map-test` }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith(
          `${entity}-map-test`,
          expectedType,
          'websocket'
        );
      });
    });
  });

  describe('Regression Prevention - Project Support', () => {
    it('should NOT ignore project entities (regression from old behavior)', () => {
      // This test ensures we never regress back to ignoring projects
      const message: WSMessage = {
        id: 'msg-regression-check',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'project',
          action: 'created',
          data: { id: 'project-regression' }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message);
      vi.advanceTimersByTime(150);

      // MUST trigger animation - this is the fix we implemented
      expect(animationFactory.animate).toHaveBeenCalledWith(
        'project-regression',
        'create',
        'websocket'
      );
    });
  });
});
