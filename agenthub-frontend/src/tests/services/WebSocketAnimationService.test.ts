import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { webSocketAnimationService } from '../../services/WebSocketAnimationService';
import { animationFactory } from '../../services/AnimationFactory';
import type { WSMessage } from '../../types/websocketTypes';
import logger from '../../utils/logger';

/**
 * The frame shape these cases actually hand the service - NOT a `WSMessage`.
 *
 * Two deliberate differences from `WSMessage`, and both are the SUBJECT of cases below rather than
 * slack in the fixture:
 *  - The ID walk is `primary.id` -> `data.id` -> `metadata.entity_id` (the four extract paths in
 *    `WebSocketAnimationService.ts`, at 92/141/185/228). Proving step two needs a frame with no
 *    `primary`, step three needs one with neither `primary` nor `data.id`, and "no ID found" needs all
 *    three absent - so `primary` cannot just be added to satisfy the type.
 *  - The envelope these cases wrote carries `source`/`priority`/`aiProcessed` at the TOP level and
 *    omits `version`, `sequence` and `metadata.source`.
 *
 * Typing them as what the service is handed keeps that coverage; filling the gaps in would delete it.
 * Each call re-widens through `unknown`, which is where the incompleteness is declared on purpose.
 */
type TestFrame = {
  id: string;
  type: WSMessage['type'];
  source: string;
  timestamp: string;
  priority: string;
  payload: { entity: string; action: string; data: Record<string, unknown> };
  metadata: Record<string, unknown>;
  aiProcessed: boolean;
};

// Mock dependencies
vi.mock('../../services/AnimationFactory', () => ({
  animationFactory: {
    animate: vi.fn()
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

describe('WebSocketAnimationService', () => {
  let mockWebSocketClient: any;
  let animateSpyOriginal: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Save original functions
    animateSpyOriginal = animationFactory.animate;

    // Create a fresh mock for each test
    animationFactory.animate = vi.fn().mockReturnValue(true);

    // Mock WebSocket client
    mockWebSocketClient = {
      on: vi.fn()
    };

    // Install fake timers first: useFakeTimers() replaces the global
    // requestAnimationFrame, so the synchronous stub must be applied AFTER it.
    vi.useFakeTimers();

    // Mock requestAnimationFrame and setTimeout
    vi.stubGlobal('requestAnimationFrame', (cb: Function) => {
      cb();
    });
  });

  afterEach(() => {
    // Restore original functions
    animationFactory.animate = animateSpyOriginal;
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  describe('init', () => {
    it('should register WebSocket update listener', () => {
      webSocketAnimationService.init(mockWebSocketClient);

      expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
    });

    it('should handle update messages when received', () => {
      // init() is idempotent: the previous test already registered the handler,
      // so reaching the service through its public message API is what matters here.
      webSocketAnimationService.init(mockWebSocketClient);

      // Create test message
      const testMessage: TestFrame = {
        id: 'test-123',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            id: 'task-123'
          }
        },
        metadata: {
          entity_id: 'task-123',
          task_title: 'Test Task',
          parent_branch_title: 'Test Branch'
        },
        aiProcessed: false
      };

      // Trigger message handling
      webSocketAnimationService.handleWebSocketMessage(testMessage as unknown as WSMessage);

      // Fast-forward timers to trigger deferred animation
      vi.advanceTimersByTime(150);

      // Verify animation was triggered
      expect(animationFactory.animate).toHaveBeenCalledWith('task-123', 'create', 'websocket');
    });

    it('should not register a second listener on duplicate init', () => {
      webSocketAnimationService.init(mockWebSocketClient);
      const otherClient = { on: vi.fn() };

      webSocketAnimationService.init(otherClient);

      expect(otherClient.on).not.toHaveBeenCalled();
    });
  });

  describe('handleWebSocketMessage', () => {
    describe('task animations', () => {
      it('should trigger create animation for task created', () => {
        const message: TestFrame = {
          id: 'msg-1',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: {
              id: 'task-456'
            }
          },
          metadata: {
            entity_id: 'task-456',
            task_title: 'New Task'
          },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-456', 'create', 'websocket');
      });

      it('should trigger update animation for task updated', () => {
        const message: TestFrame = {
          id: 'msg-2',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'updated',
            data: {
              primary: {
                id: 'task-789'
              }
            }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-789', 'update', 'websocket');
      });

      it('should trigger complete animation for task completed', () => {
        const message: TestFrame = {
          id: 'msg-3',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'completed',
            data: {
              id: 'task-101'
            }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-101', 'complete', 'websocket');
      });

      it('should trigger delete animation for task deleted', () => {
        const message: TestFrame = {
          id: 'msg-4',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'deleted',
            data: {
              id: 'task-202'
            }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-202', 'delete', 'websocket');
      });
    });

    describe('subtask animations', () => {
      it('should skip create animation for subtask created (mount animation handles it)', () => {
        const message: TestFrame = {
          id: 'msg-5',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'subtask',
            action: 'created',
            data: {
              id: 'subtask-123'
            }
          },
          metadata: {
            entity_id: 'subtask-123',
            subtask_title: 'Test Subtask',
            parent_task_title: 'Parent Task'
          },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled();
      });
    });

    describe('branch animations', () => {
      it('should skip create animation for branch created (mount animation handles it)', () => {
        const message: TestFrame = {
          id: 'msg-6',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'branch',
            action: 'created',
            data: {
              id: 'branch-123'
            }
          },
          metadata: {
            entity_id: 'branch-123',
            branch_title: 'Test Branch'
          },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled();
      });
    });

    describe('entity ID extraction', () => {
      it('should extract ID from primary object', () => {
        const message: TestFrame = {
          id: 'msg-7',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: {
              primary: {
                id: 'primary-id-123'
              }
            }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('primary-id-123', 'create', 'websocket');
      });

      it('should extract ID from data directly', () => {
        const message: TestFrame = {
          id: 'msg-8',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: {
              id: 'direct-id-123'
            }
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('direct-id-123', 'create', 'websocket');
      });

      it('should extract ID from metadata', () => {
        const message: TestFrame = {
          id: 'msg-9',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: {}
          },
          metadata: {
            entity_id: 'metadata-id-123'
          },
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('metadata-id-123', 'create', 'websocket');
      });

      it('should not trigger animation if no ID found', () => {
        const message: TestFrame = {
          id: 'msg-10',
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: {
            entity: 'task',
            action: 'created',
            data: {}
          },
          metadata: {},
          aiProcessed: false
        };

        webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled();
      });
    });

    it('should ignore messages for unsupported entities', () => {
      // Use a truly unsupported entity type (projects are NOW supported!)
      const message: TestFrame = {
        id: 'msg-11',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'unknown_entity',
          action: 'created',
          data: {
            id: 'unknown-123'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).not.toHaveBeenCalled();
    });

    it('should ignore messages with unsupported actions', () => {
      const message: TestFrame = {
        id: 'msg-12',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'archived',
          data: {
            id: 'task-123'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).not.toHaveBeenCalled();
    });
  });

  describe('event listeners', () => {
    it('should register and trigger event listeners', () => {
      const listener = vi.fn();
      const unsubscribe = webSocketAnimationService.on('task-created', listener);

      const message: TestFrame = {
        id: 'msg-13',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            id: 'task-123'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);

      expect(listener).toHaveBeenCalledWith({
        action: 'created',
        message
      });

      // Test unsubscribe
      unsubscribe();
      listener.mockClear();

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('triggerTestAnimation', () => {
    it('should trigger test animations for created', () => {
      webSocketAnimationService.triggerTestAnimation('created', 'task', 'test-element-1');

      expect(animationFactory.animate).toHaveBeenCalledWith('test-element-1', 'create', 'websocket');
    });

    it('should trigger test animations for updated', () => {
      webSocketAnimationService.triggerTestAnimation('updated', 'subtask', 'test-element-2');

      expect(animationFactory.animate).toHaveBeenCalledWith('test-element-2', 'update', 'websocket');
    });

    it('should trigger test animations for completed', () => {
      webSocketAnimationService.triggerTestAnimation('completed', 'task', 'test-element-3');

      expect(animationFactory.animate).toHaveBeenCalledWith('test-element-3', 'complete', 'websocket');
    });

    it('should trigger test animations for deleted', () => {
      webSocketAnimationService.triggerTestAnimation('deleted', 'branch', 'test-element-4');

      expect(animationFactory.animate).toHaveBeenCalledWith('test-element-4', 'delete', 'websocket');
    });

    it('should emit event when triggering test animation', () => {
      const listener = vi.fn();
      webSocketAnimationService.on('task-created', listener);

      webSocketAnimationService.triggerTestAnimation('created', 'task', 'test-element-5');

      expect(listener).toHaveBeenCalledWith({
        action: 'created',
        message: expect.objectContaining({
          payload: { entity: 'task', action: 'created' },
          metadata: { entity_id: 'test-element-5' }
        })
      });
    });
  });

  describe('animation timing', () => {
    it('should defer animation execution by 150ms', () => {
      const message: TestFrame = {
        id: 'msg-14',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            id: 'task-timing-test'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);

      // Animation should not be triggered immediately
      expect(animationFactory.animate).not.toHaveBeenCalled();

      // Advance timers by less than 150ms
      vi.advanceTimersByTime(100);
      expect(animationFactory.animate).not.toHaveBeenCalled();

      // Advance to exactly 150ms
      vi.advanceTimersByTime(50);
      expect(animationFactory.animate).toHaveBeenCalledWith('task-timing-test', 'create', 'websocket');
    });
  });

  describe('message bursts', () => {
    it('should animate every message of a rapid burst', () => {
      for (let i = 0; i < 100; i++) {
        webSocketAnimationService.handleWebSocketMessage({
          id: `burst-${i}`,
          type: 'update',
          source: 'backend',
          timestamp: new Date().toISOString(),
          priority: 'normal',
          payload: { entity: 'task', action: 'updated', data: { id: `task-${i}` } },
          metadata: { entity_id: `task-${i}` },
          aiProcessed: false
        } as unknown as WSMessage);
      }
      vi.advanceTimersByTime(200);

      expect(animationFactory.animate).toHaveBeenCalledTimes(100);
    });
  });

  describe('edge cases', () => {
    it('should handle primary as array gracefully', () => {
      const message: TestFrame = {
        id: 'msg-15',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            primary: ['not-an-object'],
            id: 'fallback-id'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message as unknown as WSMessage);
      vi.advanceTimersByTime(150);

      // Should use fallback ID
      expect(animationFactory.animate).toHaveBeenCalledWith('fallback-id', 'create', 'websocket');
    });

    it('should handle both delete and deleted actions', () => {
      const deleteMessage: TestFrame = {
        id: 'msg-16',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'delete',
          data: {
            id: 'task-delete-1'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      const deletedMessage: TestFrame = {
        id: 'msg-17',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            id: 'task-delete-2'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(deleteMessage as unknown as WSMessage);
      webSocketAnimationService.handleWebSocketMessage(deletedMessage as unknown as WSMessage);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith('task-delete-1', 'delete', 'websocket');
      expect(animationFactory.animate).toHaveBeenCalledWith('task-delete-2', 'delete', 'websocket');
    });
  });

  describe('a frame the service has no animation route for', () => {
    // The server reports a REFUSED notification as an error frame: payload.entity 'system' with a code
    // (NOT_AUTHORIZED, notification_blocked) and the entity it was about. Dropping it in silence is how a
    // server-side refusal became indistinguishable, on the client, from an animation that never fired.
    const errorFrame = {
      type: 'error',
      payload: {
        entity: 'system',
        action: 'notification_blocked',
        data: {
          primary: {
            code: 'NOT_AUTHORIZED',
            message: "Notification blocked: You don't have access to this task",
            entity_type: 'task',
            entity_id: 'task-refused-1',
            event_type: 'updated',
            reason: 'Authorization check failed'
          }
        }
      },
      metadata: { source: 'system' }
    } as unknown as WSMessage;

    it('reports the server\'s own explanation instead of dropping it', () => {
      webSocketAnimationService.handleWebSocketMessage(errorFrame);

      expect(logger.warn).toHaveBeenCalledTimes(1);
      const [, context] = vi.mocked(logger.warn).mock.calls[0];
      expect(context).toMatchObject({
        code: 'NOT_AUTHORIZED',
        entity_id: 'task-refused-1',
        entity_type: 'task',
        event_type: 'updated'
      });
      expect(animationFactory.animate).not.toHaveBeenCalled();
    });

    it('does NOT report a heartbeat, which is also entity system', () => {
      webSocketAnimationService.handleWebSocketMessage({
        type: 'heartbeat',
        payload: { entity: 'system', action: 'pong', data: { primary: { status: 'alive' } } },
        metadata: { source: 'system' }
      } as unknown as WSMessage);

      expect(logger.warn).not.toHaveBeenCalled();
    });

    it('does NOT report an ordinary frame it routes, like a task update', () => {
      webSocketAnimationService.handleWebSocketMessage({
        type: 'update',
        payload: { entity: 'task', action: 'updated', data: { primary: { id: 'task-ok-1' } } },
        metadata: { source: 'user' }
      } as unknown as WSMessage);

      expect(logger.warn).not.toHaveBeenCalled();
    });
  });
});
