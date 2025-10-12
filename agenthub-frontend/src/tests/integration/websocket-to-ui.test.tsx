import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { BrowserRouter } from 'react-router-dom';
import { AuthContext } from '../../contexts/AuthContext';
import LazyTaskList from '../../components/LazyTaskList';
import { WebSocketClient, WSMessage } from '../../services/WebSocketClient';
import { changePoolService } from '../../services/changePoolService';
import webSocketSlice from '../../store/slices/webSocketSlice';
import cascadeSlice from '../../store/slices/cascadeSlice';

// Mock all external dependencies
jest.mock('../../services/WebSocketClient');
jest.mock('../../services/WebSocketAnimationService');
jest.mock('../../services/changePoolService');
jest.mock('../../services/notificationService');
jest.mock('../../api');
jest.mock('../../api-lazy');

// Mock console to reduce noise
const mockConsole = {
  log: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn()
};

beforeEach(() => {
  global.console = mockConsole as any;
});

afterEach(() => {
  jest.restoreAllMocks();
  jest.clearAllMocks();
});

// Test store setup
const createTestStore = (initialState = {}) => configureStore({
  reducer: {
    webSocket: webSocketSlice,
    cascade: cascadeSlice
  },
  preloadedState: {
    webSocket: {
      isConnected: true,
      isReconnecting: false,
      error: null,
      messages: []
    },
    cascade: {
      branches: {},
      tasks: {},
      projects: {},
      subtasks: {},
      contexts: {}
    },
    ...initialState
  }
});

// Mock auth context
const mockAuthContext = {
  user: { id: 'test-user-123', email: 'test@example.com' },
  tokens: { access_token: 'test-token-abc', refresh_token: 'refresh-123' },
  login: jest.fn(),
  logout: jest.fn(),
  isLoading: false,
  error: null
};

// Test wrapper component
const createTestWrapper = (store = createTestStore()) => {
  return ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <AuthContext.Provider value={mockAuthContext}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </AuthContext.Provider>
    </Provider>
  );
};

// Mock WebSocket client
let mockWebSocketClient: any;
let eventHandlers: Map<string, Function> = new Map();

const createMockWebSocketClient = () => {
  eventHandlers.clear();

  mockWebSocketClient = {
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn(),
    resetReconnectAttempts: jest.fn(),
    isConnected: jest.fn().mockReturnValue(true),
    on: jest.fn((event: string, handler: Function) => {
      eventHandlers.set(event, handler);
    }),
    off: jest.fn(),
    emit: jest.fn((event: string, data?: any) => {
      const handler = eventHandlers.get(event);
      if (handler) handler(data);
    }),
    getConfig: jest.fn().mockReturnValue({
      maxReconnectAttempts: 5,
      reconnectDelay: 1000,
      aiBufferTimeout: 500,
      maxReconnectDelay: 30000,
      heartbeatInterval: 30000
    })
  };

  (WebSocketClient as jest.MockedClass<typeof WebSocketClient>).mockImplementation(() => mockWebSocketClient);
  return mockWebSocketClient;
};

// Mock API responses
jest.mock('../../api', () => ({
  listTasks: jest.fn().mockResolvedValue({
    success: true,
    data: { tasks: [], total: 0 }
  }),
  createTask: jest.fn(),
  updateTask: jest.fn(),
  deleteTask: jest.fn(),
  getAvailableAgents: jest.fn().mockResolvedValue([]),
  listAgents: jest.fn().mockResolvedValue([])
}));

// Mock change pool service
let changeListeners: Function[] = [];
(changePoolService as any) = {
  subscribe: jest.fn((listener: Function) => {
    changeListeners.push(listener);
    return () => {
      changeListeners = changeListeners.filter(l => l !== listener);
    };
  }),
  notifyChange: jest.fn((notification: any) => {
    changeListeners.forEach(listener => listener(notification));
  })
};

describe('WebSocket to UI Integration Tests', () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    createMockWebSocketClient();

    // Mock change pool service initialization
    jest.requireMock('../../services/changePoolService').initializeWebSocketIntegration = jest.fn(() => jest.fn());
  });

  afterEach(() => {
    changeListeners = [];
  });

  describe('WebSocket CREATE message → changePoolService → LazyTaskList → DOM update', () => {
    it('should add new task to UI when WebSocket CREATE message received', async () => {
      // Render LazyTaskList
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      // Simulate WebSocket CREATE message
      const createMessage: WSMessage = {
        id: 'msg-create-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: {
              id: 'new-task-123',
              title: 'New WebSocket Task',
              status: 'todo',
              priority: 'high',
              git_branch_id: 'test-branch-456',
              assignees: ['test-agent'],
              created_at: new Date().toISOString()
            }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'test-branch-456',
          entity_type: 'task',
          entity_id: 'new-task-123'
        }
      };

      // Trigger WebSocket message
      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(createMessage);
        }
      });

      // Simulate change pool notification
      act(() => {
        changePoolService.notifyChange({
          type: 'task_created',
          entity: 'task',
          entityId: 'new-task-123',
          branchId: 'test-branch-456',
          data: createMessage.payload.data.primary
        });
      });

      // Verify new task appears in DOM
      await waitFor(() => {
        expect(screen.getByText('New WebSocket Task')).toBeInTheDocument();
      });

      // Verify task status and priority are displayed
      expect(screen.getByText('todo')).toBeInTheDocument();
      expect(screen.getByText('high')).toBeInTheDocument();
    });

    it('should handle multiple rapid CREATE messages correctly', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      // Create multiple tasks rapidly
      const tasks = [
        { id: 'task-1', title: 'Task One' },
        { id: 'task-2', title: 'Task Two' },
        { id: 'task-3', title: 'Task Three' }
      ];

      tasks.forEach((task, index) => {
        const createMessage: WSMessage = {
          id: `msg-create-${index}`,
          version: '2.0',
          type: 'update',
          timestamp: new Date().toISOString(),
          sequence: index + 1,
          payload: {
            entity: 'task',
            action: 'create',
            data: {
              primary: {
                id: task.id,
                title: task.title,
                status: 'todo',
                priority: 'medium',
                git_branch_id: 'test-branch-456'
              }
            }
          },
          metadata: {
            source: 'user',
            parent_branch_id: 'test-branch-456'
          }
        };

        act(() => {
          const updateHandler = eventHandlers.get('update');
          if (updateHandler) {
            updateHandler(createMessage);
          }
        });

        act(() => {
          changePoolService.notifyChange({
            type: 'task_created',
            entity: 'task',
            entityId: task.id,
            branchId: 'test-branch-456',
            data: createMessage.payload.data.primary
          });
        });
      });

      // All tasks should appear
      await waitFor(() => {
        expect(screen.getByText('Task One')).toBeInTheDocument();
        expect(screen.getByText('Task Two')).toBeInTheDocument();
        expect(screen.getByText('Task Three')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket UPDATE message → changePoolService → LazyTaskList → DOM update', () => {
    it('should update existing task in UI when WebSocket UPDATE message received', async () => {
      // Initial state with existing task
      const initialStore = createTestStore({
        cascade: {
          tasks: {
            'existing-task-123': {
              id: 'existing-task-123',
              title: 'Original Task Title',
              status: 'todo',
              priority: 'low',
              git_branch_id: 'test-branch-456'
            }
          }
        }
      });

      // Mock API to return existing task
      jest.requireMock('../../api').listTasks.mockResolvedValue({
        success: true,
        data: {
          tasks: [{
            id: 'existing-task-123',
            title: 'Original Task Title',
            status: 'todo',
            priority: 'low',
            git_branch_id: 'test-branch-456'
          }],
          total: 1
        }
      });

      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(initialStore) }
      );

      await waitFor(() => {
        expect(screen.getByText('Original Task Title')).toBeInTheDocument();
      });

      // Send UPDATE message
      const updateMessage: WSMessage = {
        id: 'msg-update-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 2,
        payload: {
          entity: 'task',
          action: 'update',
          data: {
            primary: {
              id: 'existing-task-123',
              title: 'Updated Task Title',
              status: 'in_progress',
              priority: 'high',
              git_branch_id: 'test-branch-456'
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          parent_branch_id: 'test-branch-456'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(updateMessage);
        }
      });

      act(() => {
        changePoolService.notifyChange({
          type: 'task_updated',
          entity: 'task',
          entityId: 'existing-task-123',
          branchId: 'test-branch-456',
          data: updateMessage.payload.data.primary
        });
      });

      // Verify task was updated
      await waitFor(() => {
        expect(screen.getByText('Updated Task Title')).toBeInTheDocument();
        expect(screen.queryByText('Original Task Title')).not.toBeInTheDocument();
      });

      expect(screen.getByText('in_progress')).toBeInTheDocument();
      expect(screen.getByText('high')).toBeInTheDocument();
    });

    it('should handle status transitions with animations', async () => {
      const initialStore = createTestStore({
        cascade: {
          tasks: {
            'status-task-123': {
              id: 'status-task-123',
              title: 'Status Task',
              status: 'todo',
              priority: 'medium'
            }
          }
        }
      });

      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(initialStore) }
      );

      // Test multiple status transitions
      const statusUpdates = [
        { status: 'in_progress', sequence: 1 },
        { status: 'review', sequence: 2 },
        { status: 'done', sequence: 3 }
      ];

      for (const update of statusUpdates) {
        const updateMessage: WSMessage = {
          id: `msg-status-${update.sequence}`,
          version: '2.0',
          type: 'update',
          timestamp: new Date().toISOString(),
          sequence: update.sequence,
          payload: {
            entity: 'task',
            action: 'update',
            data: {
              primary: {
                id: 'status-task-123',
                title: 'Status Task',
                status: update.status,
                priority: 'medium'
              }
            }
          },
          metadata: {
            source: 'user',
            parent_branch_id: 'test-branch-456'
          }
        };

        act(() => {
          const updateHandler = eventHandlers.get('update');
          if (updateHandler) {
            updateHandler(updateMessage);
          }
        });

        act(() => {
          changePoolService.notifyChange({
            type: 'task_updated',
            entity: 'task',
            entityId: 'status-task-123',
            branchId: 'test-branch-456',
            data: updateMessage.payload.data.primary
          });
        });

        await waitFor(() => {
          expect(screen.getByText(update.status)).toBeInTheDocument();
        });
      }
    });
  });

  describe('WebSocket DELETE message → changePoolService → LazyTaskList → DOM removal', () => {
    it('should remove task from UI when WebSocket DELETE message received', async () => {
      // Start with task in the UI
      const initialStore = createTestStore({
        cascade: {
          tasks: {
            'delete-task-123': {
              id: 'delete-task-123',
              title: 'Task to Delete',
              status: 'todo',
              priority: 'medium'
            }
          }
        }
      });

      jest.requireMock('../../api').listTasks.mockResolvedValue({
        success: true,
        data: {
          tasks: [{
            id: 'delete-task-123',
            title: 'Task to Delete',
            status: 'todo',
            priority: 'medium'
          }],
          total: 1
        }
      });

      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(initialStore) }
      );

      await waitFor(() => {
        expect(screen.getByText('Task to Delete')).toBeInTheDocument();
      });

      // Send DELETE message
      const deleteMessage: WSMessage = {
        id: 'msg-delete-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 3,
        payload: {
          entity: 'task',
          action: 'delete',
          data: {
            primary: {
              id: 'delete-task-123'
            }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'test-branch-456'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(deleteMessage);
        }
      });

      act(() => {
        changePoolService.notifyChange({
          type: 'task_deleted',
          entity: 'task',
          entityId: 'delete-task-123',
          branchId: 'test-branch-456',
          data: deleteMessage.payload.data.primary
        });
      });

      // Verify task is removed from DOM
      await waitFor(() => {
        expect(screen.queryByText('Task to Delete')).not.toBeInTheDocument();
      });
    });

    it('should handle DELETE with animation timing', async () => {
      // Mock animation timing
      jest.useFakeTimers();

      const initialStore = createTestStore({
        cascade: {
          tasks: {
            'animate-delete-123': {
              id: 'animate-delete-123',
              title: 'Animated Delete Task',
              status: 'todo',
              priority: 'medium'
            }
          }
        }
      });

      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(initialStore) }
      );

      // Send DELETE message
      const deleteMessage: WSMessage = {
        id: 'msg-animate-delete',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'delete',
          data: {
            primary: { id: 'animate-delete-123' }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'test-branch-456'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(deleteMessage);
        }
      });

      // Fast forward through animation timing
      act(() => {
        jest.advanceTimersByTime(1000); // Delete animation duration
      });

      jest.useRealTimers();
    });
  });

  describe('Multiple rapid WebSocket messages update UI correctly', () => {
    it('should handle mixed CREATE, UPDATE, DELETE operations in sequence', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      // Sequence of operations
      const operations = [
        {
          type: 'create',
          message: {
            id: 'seq-1',
            version: '2.0' as const,
            type: 'update' as const,
            timestamp: new Date().toISOString(),
            sequence: 1,
            payload: {
              entity: 'task',
              action: 'create',
              data: {
                primary: {
                  id: 'seq-task-1',
                  title: 'Sequential Task 1',
                  status: 'todo',
                  priority: 'high'
                }
              }
            },
            metadata: {
              source: 'user' as const,
              parent_branch_id: 'test-branch-456'
            }
          }
        },
        {
          type: 'update',
          message: {
            id: 'seq-2',
            version: '2.0' as const,
            type: 'update' as const,
            timestamp: new Date().toISOString(),
            sequence: 2,
            payload: {
              entity: 'task',
              action: 'update',
              data: {
                primary: {
                  id: 'seq-task-1',
                  title: 'Updated Sequential Task 1',
                  status: 'in_progress',
                  priority: 'high'
                }
              }
            },
            metadata: {
              source: 'mcp-ai' as const,
              parent_branch_id: 'test-branch-456'
            }
          }
        },
        {
          type: 'delete',
          message: {
            id: 'seq-3',
            version: '2.0' as const,
            type: 'update' as const,
            timestamp: new Date().toISOString(),
            sequence: 3,
            payload: {
              entity: 'task',
              action: 'delete',
              data: {
                primary: { id: 'seq-task-1' }
              }
            },
            metadata: {
              source: 'user' as const,
              parent_branch_id: 'test-branch-456'
            }
          }
        }
      ];

      // Execute sequence
      for (const operation of operations) {
        act(() => {
          const updateHandler = eventHandlers.get('update');
          if (updateHandler) {
            updateHandler(operation.message);
          }
        });

        act(() => {
          const notificationType = operation.type === 'create' ? 'task_created' :
                                   operation.type === 'update' ? 'task_updated' : 'task_deleted';

          changePoolService.notifyChange({
            type: notificationType,
            entity: 'task',
            entityId: 'seq-task-1',
            branchId: 'test-branch-456',
            data: operation.message.payload.data.primary
          });
        });

        // Small delay between operations
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      // After sequence, task should be gone
      await waitFor(() => {
        expect(screen.queryByText('Sequential Task 1')).not.toBeInTheDocument();
        expect(screen.queryByText('Updated Sequential Task 1')).not.toBeInTheDocument();
      });
    });

    it('should handle batch updates efficiently', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Batch message with multiple tasks
      const batchMessage: WSMessage = {
        id: 'batch-1',
        version: '2.0',
        type: 'bulk',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'multiple',
          action: 'update',
          data: {
            primary: [
              {
                id: 'batch-task-1',
                title: 'Batch Task 1',
                status: 'todo',
                priority: 'medium'
              },
              {
                id: 'batch-task-2',
                title: 'Batch Task 2',
                status: 'in_progress',
                priority: 'high'
              },
              {
                id: 'batch-task-3',
                title: 'Batch Task 3',
                status: 'done',
                priority: 'low'
              }
            ]
          }
        },
        metadata: {
          source: 'mcp-ai',
          batchId: 'batch-123'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(batchMessage);
        }
      });

      // Notify about batch changes
      act(() => {
        batchMessage.payload.data.primary.forEach((task: any) => {
          changePoolService.notifyChange({
            type: 'task_created',
            entity: 'task',
            entityId: task.id,
            branchId: 'test-branch-456',
            data: task
          });
        });
      });

      // All batch tasks should appear
      await waitFor(() => {
        expect(screen.getByText('Batch Task 1')).toBeInTheDocument();
        expect(screen.getByText('Batch Task 2')).toBeInTheDocument();
        expect(screen.getByText('Batch Task 3')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket reconnection preserves UI state', () => {
    it('should maintain UI state during reconnection', async () => {
      const initialStore = createTestStore({
        webSocket: {
          isConnected: true,
          isReconnecting: false,
          error: null,
          messages: []
        },
        cascade: {
          tasks: {
            'persist-task-123': {
              id: 'persist-task-123',
              title: 'Persistent Task',
              status: 'in_progress',
              priority: 'high'
            }
          }
        }
      });

      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(initialStore) }
      );

      await waitFor(() => {
        expect(screen.getByText('Persistent Task')).toBeInTheDocument();
      });

      // Simulate disconnection
      act(() => {
        store.dispatch({
          type: 'webSocket/disconnected'
        });
        store.dispatch({
          type: 'webSocket/reconnecting'
        });
      });

      // Task should still be visible during reconnection
      expect(screen.getByText('Persistent Task')).toBeInTheDocument();

      // Simulate reconnection
      act(() => {
        store.dispatch({
          type: 'webSocket/connected',
          payload: {}
        });
      });

      // Task should still be present after reconnection
      expect(screen.getByText('Persistent Task')).toBeInTheDocument();
    });

    it('should resume live updates after reconnection', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Simulate reconnection event
      act(() => {
        const connectedHandler = eventHandlers.get('connected');
        if (connectedHandler) {
          connectedHandler();
        }
      });

      // Send message after reconnection
      const postReconnectMessage: WSMessage = {
        id: 'post-reconnect-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: {
              id: 'post-reconnect-task',
              title: 'Post Reconnect Task',
              status: 'todo',
              priority: 'medium'
            }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'test-branch-456'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(postReconnectMessage);
        }
      });

      act(() => {
        changePoolService.notifyChange({
          type: 'task_created',
          entity: 'task',
          entityId: 'post-reconnect-task',
          branchId: 'test-branch-456',
          data: postReconnectMessage.payload.data.primary
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Post Reconnect Task')).toBeInTheDocument();
      });
    });
  });

  describe('Error handling and edge cases', () => {
    it('should handle WebSocket errors gracefully', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Simulate WebSocket error
      act(() => {
        const errorHandler = eventHandlers.get('error');
        if (errorHandler) {
          errorHandler(new Error('Connection failed'));
        }
      });

      // UI should still be functional
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });
    });

    it('should handle malformed WebSocket messages', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Send malformed message
      const malformedMessage = {
        id: 'malformed',
        // Missing required fields
      } as WSMessage;

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(malformedMessage);
        }
      });

      // Should not crash
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });
    });

    it('should handle messages for different branches correctly', async () => {
      render(
        <LazyTaskList
          projectId="test-project-123"
          taskTreeId="test-branch-456"
        />,
        { wrapper: createTestWrapper(store) }
      );

      // Message for different branch - should be ignored
      const differentBranchMessage: WSMessage = {
        id: 'different-branch',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: {
              id: 'different-branch-task',
              title: 'Different Branch Task',
              git_branch_id: 'different-branch-789'
            }
          }
        },
        metadata: {
          source: 'user',
          parent_branch_id: 'different-branch-789'
        }
      };

      act(() => {
        const updateHandler = eventHandlers.get('update');
        if (updateHandler) {
          updateHandler(differentBranchMessage);
        }
      });

      // Task should not appear because it's for a different branch
      await waitFor(() => {
        expect(screen.queryByText('Different Branch Task')).not.toBeInTheDocument();
      });
    });
  });
});