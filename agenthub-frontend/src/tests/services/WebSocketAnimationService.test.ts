import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { webSocketAnimationService } from '../../services/WebSocketAnimationService';
import { animationFactory } from '../../services/AnimationFactory';
import type { WSMessage } from '../../types/websocketTypes';

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

    // Mock requestAnimationFrame and setTimeout
    vi.stubGlobal('requestAnimationFrame', (cb: Function) => {
      cb();
    });
    vi.useFakeTimers();
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
      webSocketAnimationService.init(mockWebSocketClient);
      
      // Get the registered callback
      const updateCallback = mockWebSocketClient.on.mock.calls[0][1];
      
      // Create test message
      const testMessage: WSMessage = {
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

      // Trigger the callback
      updateCallback(testMessage);
      
      // Fast-forward timers to trigger deferred animation
      vi.advanceTimersByTime(150);
      
      // Verify animation was triggered
      expect(animationFactory.animate).toHaveBeenCalledWith('task-123', 'create', 'websocket');
    });
  });

  describe('handleWebSocketMessage', () => {
    describe('task animations', () => {
      it('should trigger create animation for task created', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-456', 'create', 'websocket');
      });

      it('should trigger update animation for task updated', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-789', 'update', 'websocket');
      });

      it('should trigger complete animation for task completed', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-101', 'complete', 'websocket');
      });

      it('should trigger delete animation for task deleted', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('task-202', 'delete', 'websocket');
      });
    });

    describe('subtask animations', () => {
      it('should trigger animations for subtask operations', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('subtask-123', 'create', 'websocket');
      });
    });

    describe('branch animations', () => {
      it('should trigger animations for branch operations', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('branch-123', 'create', 'websocket');
      });
    });

    describe('entity ID extraction', () => {
      it('should extract ID from primary object', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('primary-id-123', 'create', 'websocket');
      });

      it('should extract ID from data directly', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('direct-id-123', 'create', 'websocket');
      });

      it('should extract ID from metadata', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).toHaveBeenCalledWith('metadata-id-123', 'create', 'websocket');
      });

      it('should not trigger animation if no ID found', () => {
        const message: WSMessage = {
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

        webSocketAnimationService.handleWebSocketMessage(message);
        vi.advanceTimersByTime(150);

        expect(animationFactory.animate).not.toHaveBeenCalled();
      });
    });

    it('should ignore messages for unsupported entities', () => {
      const message: WSMessage = {
        id: 'msg-11',
        type: 'update',
        source: 'backend',
        timestamp: new Date().toISOString(),
        priority: 'normal',
        payload: {
          entity: 'project',
          action: 'created',
          data: {
            id: 'project-123'
          }
        },
        metadata: {},
        aiProcessed: false
      };

      webSocketAnimationService.handleWebSocketMessage(message);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).not.toHaveBeenCalled();
    });

    it('should ignore messages with unsupported actions', () => {
      const message: WSMessage = {
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

      webSocketAnimationService.handleWebSocketMessage(message);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).not.toHaveBeenCalled();
    });
  });

  describe('event listeners', () => {
    it('should register and trigger event listeners', () => {
      const listener = vi.fn();
      const unsubscribe = webSocketAnimationService.on('task-created', listener);

      const message: WSMessage = {
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

      webSocketAnimationService.handleWebSocketMessage(message);

      expect(listener).toHaveBeenCalledWith({
        action: 'created',
        message
      });

      // Test unsubscribe
      unsubscribe();
      listener.mockClear();
      
      webSocketAnimationService.handleWebSocketMessage(message);
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
      const message: WSMessage = {
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

      webSocketAnimationService.handleWebSocketMessage(message);
      
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

  describe('edge cases', () => {
    it('should handle primary as array gracefully', () => {
      const message: WSMessage = {
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

      webSocketAnimationService.handleWebSocketMessage(message);
      vi.advanceTimersByTime(150);

      // Should use fallback ID
      expect(animationFactory.animate).toHaveBeenCalledWith('fallback-id', 'create', 'websocket');
    });

    it('should handle both delete and deleted actions', () => {
      const deleteMessage: WSMessage = {
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

      const deletedMessage: WSMessage = {
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

      webSocketAnimationService.handleWebSocketMessage(deleteMessage);
      webSocketAnimationService.handleWebSocketMessage(deletedMessage);
      vi.advanceTimersByTime(150);

      expect(animationFactory.animate).toHaveBeenCalledWith('task-delete-1', 'delete', 'websocket');
      expect(animationFactory.animate).toHaveBeenCalledWith('task-delete-2', 'delete', 'websocket');
    });
  });
});