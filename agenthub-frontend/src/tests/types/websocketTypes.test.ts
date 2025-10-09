import { describe, it, expect } from 'vitest';
import type { WebSocketConfig, WSMessage } from '../../types/websocketTypes';

describe('websocketTypes', () => {
  describe('WebSocketConfig', () => {
    it('should have correct structure for WebSocketConfig', () => {
      const config: WebSocketConfig = {
        maxReconnectAttempts: 5,
        reconnectDelay: 1000,
        aiBufferTimeout: 500,
        maxReconnectDelay: 30000,
        heartbeatInterval: 60000
      };

      expect(config.maxReconnectAttempts).toBe(5);
      expect(config.reconnectDelay).toBe(1000);
      expect(config.aiBufferTimeout).toBe(500);
      expect(config.maxReconnectDelay).toBe(30000);
      expect(config.heartbeatInterval).toBe(60000);
    });
  });

  describe('WSMessage', () => {
    it('should have correct structure for update message', () => {
      const message: WSMessage = {
        id: 'msg-123',
        version: '2.0',
        type: 'update',
        timestamp: '2025-01-10T10:00:00Z',
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            id: 'task-123',
            primary: {
              id: 'task-123',
              title: 'Test Task',
              status: 'todo'
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          userId: 'user-123',
          sessionId: 'session-123',
          entity_id: 'task-123',
          task_title: 'Test Task'
        }
      };

      expect(message.version).toBe('2.0');
      expect(message.type).toBe('update');
      expect(message.payload.entity).toBe('task');
      expect(message.payload.action).toBe('created');
      expect(message.payload.data.id).toBe('task-123');
      expect(message.metadata.source).toBe('mcp-ai');
    });

    it('should support all message types', () => {
      const messageTypes: WSMessage['type'][] = ['update', 'bulk', 'sync', 'heartbeat', 'error'];
      
      messageTypes.forEach(type => {
        const message: WSMessage = {
          id: 'msg-456',
          version: '2.0',
          type,
          timestamp: new Date().toISOString(),
          sequence: 1,
          payload: {
            entity: 'test',
            action: 'test',
            data: {
              primary: {}
            }
          },
          metadata: {
            source: 'system'
          }
        };

        expect(message.type).toBe(type);
      });
    });

    it('should support cascade data structure', () => {
      const message: WSMessage = {
        id: 'msg-789',
        version: '2.0',
        type: 'bulk',
        timestamp: new Date().toISOString(),
        sequence: 2,
        payload: {
          entity: 'project',
          action: 'sync',
          data: {
            primary: { id: 'project-123', name: 'Test Project' },
            cascade: {
              branches: [{ id: 'branch-1', name: 'main' }],
              tasks: [{ id: 'task-1', title: 'Task 1' }],
              projects: [],
              subtasks: [{ id: 'subtask-1', title: 'Subtask 1' }],
              contexts: [{ id: 'context-1', data: {} }]
            }
          }
        },
        metadata: {
          source: 'system',
          batchId: 'batch-123'
        }
      };

      expect(message.payload.data.cascade).toBeDefined();
      expect(message.payload.data.cascade?.branches).toHaveLength(1);
      expect(message.payload.data.cascade?.tasks).toHaveLength(1);
      expect(message.payload.data.cascade?.subtasks).toHaveLength(1);
      expect(message.payload.data.cascade?.contexts).toHaveLength(1);
    });

    it('should support primary as array', () => {
      const message: WSMessage = {
        id: 'msg-array',
        version: '2.0',
        type: 'bulk',
        timestamp: new Date().toISOString(),
        sequence: 3,
        payload: {
          entity: 'tasks',
          action: 'list',
          data: {
            primary: [
              { id: 'task-1', title: 'Task 1' },
              { id: 'task-2', title: 'Task 2' }
            ]
          }
        },
        metadata: {
          source: 'user'
        }
      };

      expect(Array.isArray(message.payload.data.primary)).toBe(true);
      expect(message.payload.data.primary).toHaveLength(2);
    });

    it('should support all metadata sources', () => {
      const sources: WSMessage['metadata']['source'][] = ['mcp-ai', 'user', 'system'];
      
      sources.forEach(source => {
        const message: WSMessage = {
          id: 'msg-source',
          version: '2.0',
          type: 'update',
          timestamp: new Date().toISOString(),
          sequence: 1,
          payload: {
            entity: 'test',
            action: 'test',
            data: {
              primary: {}
            }
          },
          metadata: {
            source
          }
        };

        expect(message.metadata.source).toBe(source);
      });
    });

    it('should support optional metadata fields', () => {
      const message: WSMessage = {
        id: 'msg-metadata',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 4,
        payload: {
          entity: 'task',
          action: 'updated',
          data: {
            primary: { id: 'task-123' }
          }
        },
        metadata: {
          source: 'mcp-ai',
          userId: 'user-123',
          sessionId: 'session-456',
          correlationId: 'corr-789',
          batchId: 'batch-abc',
          entity_type: 'task',
          entity_id: 'task-123',
          event_type: 'update',
          task_title: 'Updated Task',
          parent_task_title: 'Parent Task'
        }
      };

      expect(message.metadata.userId).toBe('user-123');
      expect(message.metadata.sessionId).toBe('session-456');
      expect(message.metadata.correlationId).toBe('corr-789');
      expect(message.metadata.batchId).toBe('batch-abc');
      expect(message.metadata.entity_type).toBe('task');
      expect(message.metadata.entity_id).toBe('task-123');
      expect(message.metadata.event_type).toBe('update');
      expect(message.metadata.task_title).toBe('Updated Task');
      expect(message.metadata.parent_task_title).toBe('Parent Task');
    });

    it('should support subtask metadata', () => {
      const message: WSMessage = {
        id: 'msg-subtask',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 5,
        payload: {
          entity: 'subtask',
          action: 'created',
          data: {
            primary: { id: 'subtask-123' }
          }
        },
        metadata: {
          source: 'mcp-ai',
          subtask_title: 'Test Subtask',
          parent_task_title: 'Parent Task'
        }
      };

      expect(message.metadata.subtask_title).toBe('Test Subtask');
      expect(message.metadata.parent_task_title).toBe('Parent Task');
    });

    it('should support branch metadata', () => {
      const message: WSMessage = {
        id: 'msg-branch',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 6,
        payload: {
          entity: 'branch',
          action: 'created',
          data: {
            primary: { id: 'branch-123' }
          }
        },
        metadata: {
          source: 'system',
          branch_title: 'feature/new-feature',
          parent_branch_title: 'main',
          parent_branch_id: 'branch-main'
        }
      };

      expect(message.metadata.branch_title).toBe('feature/new-feature');
      expect(message.metadata.parent_branch_title).toBe('main');
      expect(message.metadata.parent_branch_id).toBe('branch-main');
    });

    it('should support dynamic data properties', () => {
      const message: WSMessage = {
        id: 'msg-dynamic',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 7,
        payload: {
          entity: 'custom',
          action: 'process',
          data: {
            primary: { id: 'custom-123' },
            customField1: 'value1',
            customField2: { nested: true },
            customArray: [1, 2, 3]
          }
        },
        metadata: {
          source: 'system'
        }
      };

      expect(message.payload.data.customField1).toBe('value1');
      expect(message.payload.data.customField2).toEqual({ nested: true });
      expect(message.payload.data.customArray).toEqual([1, 2, 3]);
    });

    it('should handle error messages', () => {
      const message: WSMessage = {
        id: 'msg-error',
        version: '2.0',
        type: 'error',
        timestamp: new Date().toISOString(),
        sequence: 8,
        payload: {
          entity: 'system',
          action: 'error',
          data: {
            primary: {
              code: 'ERR_001',
              message: 'Something went wrong',
              details: { field: 'value' }
            }
          }
        },
        metadata: {
          source: 'system',
          correlationId: 'error-corr-123'
        }
      };

      expect(message.type).toBe('error');
      expect(message.payload.data.primary.code).toBe('ERR_001');
      expect(message.payload.data.primary.message).toBe('Something went wrong');
    });

    it('should handle heartbeat messages', () => {
      const message: WSMessage = {
        id: 'msg-heartbeat',
        version: '2.0',
        type: 'heartbeat',
        timestamp: new Date().toISOString(),
        sequence: 9,
        payload: {
          entity: 'system',
          action: 'ping',
          data: {
            primary: {
              status: 'alive',
              serverTime: new Date().toISOString()
            }
          }
        },
        metadata: {
          source: 'system'
        }
      };

      expect(message.type).toBe('heartbeat');
      expect(message.payload.data.primary.status).toBe('alive');
      expect(message.payload.data.primary.serverTime).toBeDefined();
    });

    it('should enforce version 2.0', () => {
      const message: WSMessage = {
        id: 'msg-version',
        version: '2.0', // Only valid version
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 10,
        payload: {
          entity: 'test',
          action: 'test',
          data: {
            primary: {}
          }
        },
        metadata: {
          source: 'system'
        }
      };

      expect(message.version).toBe('2.0');
      // TypeScript will enforce this at compile time
    });
  });
});