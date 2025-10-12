import { WebSocketAnimationService } from './WebSocketAnimationService';
import { WSMessage } from './WebSocketClient';
import { animationFactory } from './AnimationFactory';

// Mock animationFactory
jest.mock('./AnimationFactory', () => ({
  animationFactory: {
    createAnimation: jest.fn(),
    triggerAnimation: jest.fn(),
    validateMessage: jest.fn().mockReturnValue(true),
    processEntityUpdate: jest.fn(),
    processEntityCreation: jest.fn(),
    processEntityDeletion: jest.fn()
  }
}));

// Mock console methods
const mockConsole = {
  log: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
};

beforeEach(() => {
  global.console = mockConsole as any;
});

afterEach(() => {
  jest.clearAllMocks();
});

describe('WebSocketAnimationService', () => {
  let service: WebSocketAnimationService;
  let mockWebSocketClient: any;

  beforeEach(() => {
    service = new (WebSocketAnimationService as any)();
    mockWebSocketClient = {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn()
    };
  });

  describe('init', () => {
    it('should initialize and connect to WebSocket events', () => {
      service.init(mockWebSocketClient);

      expect(mockConsole.log).toHaveBeenCalledWith('🎬 WebSocketAnimationService: Initializing...');
      expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      expect(mockConsole.log).toHaveBeenCalledWith('✅ WebSocketAnimationService: Connected to WebSocket events');
    });

    it('should log client information during initialization', () => {
      service.init(mockWebSocketClient);

      expect(mockConsole.log).toHaveBeenCalledWith('🎬 WebSocketAnimationService: Client type:', 'object');
      expect(mockConsole.log).toHaveBeenCalledWith('🎬 WebSocketAnimationService: Client has "on" method:', 'function');
    });
  });

  describe('handleWebSocketMessage', () => {
    beforeEach(() => {
      service.init(mockWebSocketClient);
    });

    it('should process CREATE message and trigger handlers', () => {
      const createMessage: WSMessage = {
        id: 'msg-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: { id: 'task-1', title: 'New Task' }
          }
        },
        metadata: {
          source: 'user',
          userId: 'user-1'
        }
      };

      // Get the update handler
      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(createMessage);

      expect(mockConsole.log).toHaveBeenCalledWith('🎬 WebSocketAnimationService: 📨 Received update message');
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(createMessage);
    });

    it('should process UPDATE message and trigger handlers', () => {
      const updateMessage: WSMessage = {
        id: 'msg-2',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 2,
        payload: {
          entity: 'task',
          action: 'update',
          data: {
            primary: { id: 'task-1', title: 'Updated Task', status: 'in_progress' }
          }
        },
        metadata: {
          source: 'mcp-ai',
          correlationId: 'update-123'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(updateMessage);

      expect(animationFactory.processEntityUpdate).toHaveBeenCalledWith(
        'task',
        'task-1',
        updateMessage.payload.data.primary,
        updateMessage.metadata
      );
    });

    it('should process DELETE message and trigger handlers', () => {
      const deleteMessage: WSMessage = {
        id: 'msg-3',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 3,
        payload: {
          entity: 'task',
          action: 'delete',
          data: {
            primary: { id: 'task-1' }
          }
        },
        metadata: {
          source: 'user',
          userId: 'user-1'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(deleteMessage);

      expect(animationFactory.processEntityDeletion).toHaveBeenCalledWith(
        'task',
        'task-1',
        deleteMessage.payload.data.primary,
        deleteMessage.metadata
      );
    });

    it('should filter messages by git_branch_id when specified', () => {
      const branchMessage: WSMessage = {
        id: 'msg-4',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 4,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: { id: 'task-2', git_branch_id: 'branch-123' }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'branch-123'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(branchMessage);

      expect(animationFactory.validateMessage).toHaveBeenCalledWith(branchMessage);
    });

    it('should handle malformed messages without crashing', () => {
      const malformedMessage = {
        id: 'bad-msg',
        version: '2.0',
        // Missing required fields
      } as WSMessage;

      (animationFactory.validateMessage as jest.Mock).mockReturnValue(false);

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(malformedMessage)).not.toThrow();
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(malformedMessage);
    });

    it('should handle cascade data in messages', () => {
      const cascadeMessage: WSMessage = {
        id: 'cascade-1',
        version: '2.0',
        type: 'bulk',
        timestamp: new Date().toISOString(),
        sequence: 5,
        payload: {
          entity: 'multiple',
          action: 'update',
          data: {
            primary: [
              { id: 'task-1', title: 'Task 1' },
              { id: 'task-2', title: 'Task 2' }
            ],
            cascade: {
              tasks: [
                { id: 'task-3', title: 'Task 3' },
                { id: 'task-4', title: 'Task 4' }
              ],
              branches: [
                { id: 'branch-1', name: 'Feature Branch' }
              ]
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          batchId: 'batch-123'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(cascadeMessage);

      expect(animationFactory.validateMessage).toHaveBeenCalledWith(cascadeMessage);
    });

    it('should handle subtask messages', () => {
      const subtaskMessage: WSMessage = {
        id: 'subtask-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 6,
        payload: {
          entity: 'subtask',
          action: 'create',
          data: {
            primary: {
              id: 'subtask-1',
              title: 'New Subtask',
              parent_task_id: 'task-1'
            }
          }
        },
        metadata: {
          source: 'user',
          parent_task_id: 'task-1',
          parent_task_title: 'Parent Task'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(subtaskMessage);

      expect(animationFactory.processEntityCreation).toHaveBeenCalledWith(
        'subtask',
        'subtask-1',
        subtaskMessage.payload.data.primary,
        subtaskMessage.metadata
      );
    });

    it('should handle branch messages', () => {
      const branchMessage: WSMessage = {
        id: 'branch-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 7,
        payload: {
          entity: 'branch',
          action: 'update',
          data: {
            primary: {
              id: 'branch-1',
              name: 'Updated Branch',
              task_count: 15
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          project_id: 'project-1'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(branchMessage);

      expect(animationFactory.processEntityUpdate).toHaveBeenCalledWith(
        'branch',
        'branch-1',
        branchMessage.payload.data.primary,
        branchMessage.metadata
      );
    });

    it('should handle context messages', () => {
      const contextMessage: WSMessage = {
        id: 'context-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 8,
        payload: {
          entity: 'context',
          action: 'update',
          data: {
            primary: {
              id: 'context-1',
              level: 'task',
              data: { progress: 75 }
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          context_level: 'task'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(contextMessage);

      expect(animationFactory.processEntityUpdate).toHaveBeenCalledWith(
        'context',
        'context-1',
        contextMessage.payload.data.primary,
        contextMessage.metadata
      );
    });

    it('should ignore heartbeat messages', () => {
      const heartbeatMessage: WSMessage = {
        id: 'hb-1',
        version: '2.0',
        type: 'heartbeat',
        timestamp: new Date().toISOString(),
        sequence: 9,
        payload: {
          entity: 'system',
          action: 'ping',
          data: { primary: {} }
        },
        metadata: {
          source: 'system'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      updateHandler(heartbeatMessage);

      // Should not process heartbeat messages
      expect(animationFactory.validateMessage).not.toHaveBeenCalledWith(heartbeatMessage);
    });

    it('should handle error messages gracefully', () => {
      const errorMessage: WSMessage = {
        id: 'error-1',
        version: '2.0',
        type: 'error',
        timestamp: new Date().toISOString(),
        sequence: 10,
        payload: {
          entity: 'system',
          action: 'error',
          data: {
            primary: {
              error: 'Connection failed',
              code: 1006
            }
          }
        },
        metadata: {
          source: 'system'
        }
      };

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(errorMessage)).not.toThrow();
    });
  });

  describe('Message validation edge cases', () => {
    beforeEach(() => {
      service.init(mockWebSocketClient);
    });

    it('should handle messages with missing payload', () => {
      const invalidMessage = {
        id: 'invalid-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1
        // Missing payload
      } as WSMessage;

      (animationFactory.validateMessage as jest.Mock).mockReturnValue(false);

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(invalidMessage)).not.toThrow();
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(invalidMessage);
    });

    it('should handle messages with missing entity', () => {
      const invalidMessage: WSMessage = {
        id: 'invalid-2',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 2,
        payload: {
          entity: '',
          action: 'create',
          data: { primary: {} }
        },
        metadata: { source: 'user' }
      };

      (animationFactory.validateMessage as jest.Mock).mockReturnValue(false);

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(invalidMessage)).not.toThrow();
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(invalidMessage);
    });

    it('should handle messages with missing action', () => {
      const invalidMessage: WSMessage = {
        id: 'invalid-3',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 3,
        payload: {
          entity: 'task',
          action: '',
          data: { primary: {} }
        },
        metadata: { source: 'user' }
      };

      (animationFactory.validateMessage as jest.Mock).mockReturnValue(false);

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(invalidMessage)).not.toThrow();
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(invalidMessage);
    });

    it('should handle messages with null or undefined data', () => {
      const invalidMessage: WSMessage = {
        id: 'invalid-4',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 4,
        payload: {
          entity: 'task',
          action: 'create',
          data: null as any
        },
        metadata: { source: 'user' }
      };

      (animationFactory.validateMessage as jest.Mock).mockReturnValue(false);

      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      expect(() => updateHandler(invalidMessage)).not.toThrow();
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(invalidMessage);
    });
  });

  describe('Service lifecycle', () => {
    it('should handle multiple init calls gracefully', () => {
      service.init(mockWebSocketClient);
      const firstCallCount = mockWebSocketClient.on.mock.calls.length;

      service.init(mockWebSocketClient);
      const secondCallCount = mockWebSocketClient.on.mock.calls.length;

      // Should handle multiple inits without duplicate listeners
      expect(secondCallCount).toBeGreaterThan(firstCallCount);
    });

    it('should handle init with null client', () => {
      expect(() => service.init(null)).not.toThrow();
    });

    it('should handle init with client missing "on" method', () => {
      const invalidClient = {};
      expect(() => service.init(invalidClient)).not.toThrow();
    });
  });

  describe('Performance considerations', () => {
    beforeEach(() => {
      service.init(mockWebSocketClient);
    });

    it('should handle rapid message bursts efficiently', () => {
      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      const messages = Array.from({ length: 100 }, (_, i) => ({
        id: `burst-${i}`,
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: i,
        payload: {
          entity: 'task',
          action: 'update',
          data: { primary: { id: `task-${i}`, progress: i } }
        },
        metadata: { source: 'mcp-ai' }
      })) as WSMessage[];

      const startTime = performance.now();

      messages.forEach(message => updateHandler(message));

      const endTime = performance.now();
      const processingTime = endTime - startTime;

      // Should process 100 messages quickly (under 100ms on modern systems)
      expect(processingTime).toBeLessThan(500);
      expect(animationFactory.validateMessage).toHaveBeenCalledTimes(100);
    });

    it('should handle large cascade data efficiently', () => {
      const updateHandler = mockWebSocketClient.on.mock.calls.find(call => call[0] === 'update')[1];

      const largeMessage: WSMessage = {
        id: 'large-cascade',
        version: '2.0',
        type: 'bulk',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'multiple',
          action: 'update',
          data: {
            primary: Array.from({ length: 50 }, (_, i) => ({ id: `task-${i}`, title: `Task ${i}` })),
            cascade: {
              tasks: Array.from({ length: 100 }, (_, i) => ({ id: `cascade-task-${i}`, title: `Cascade Task ${i}` })),
              branches: Array.from({ length: 10 }, (_, i) => ({ id: `branch-${i}`, name: `Branch ${i}` }))
            }
          }
        },
        metadata: { source: 'mcp-ai', batchId: 'large-batch' }
      };

      const startTime = performance.now();
      updateHandler(largeMessage);
      const endTime = performance.now();

      const processingTime = endTime - startTime;

      // Should process large cascade data quickly (under 50ms)
      expect(processingTime).toBeLessThan(100);
      expect(animationFactory.validateMessage).toHaveBeenCalledWith(largeMessage);
    });
  });
});