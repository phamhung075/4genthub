import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useWebSocket, useBranchWebSocket, useTaskWebSocket } from './useWebSocketV2';
import { WebSocketClient, WSMessage } from '../services/WebSocketClient';
import webSocketSlice from '../store/slices/webSocketSlice';
import cascadeSlice from '../store/slices/cascadeSlice';
import { webSocketAnimationService } from '../services/WebSocketAnimationService';
import { initializeWebSocketIntegration } from '../services/changePoolService';
import { notificationService } from '../services/notificationService';

// Mock all external dependencies
jest.mock('../services/WebSocketClient');
jest.mock('../services/WebSocketAnimationService');
jest.mock('../services/changePoolService');
jest.mock('../services/notificationService');

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
  jest.restoreAllMocks();
});

// Create a test store
const createTestStore = () => configureStore({
  reducer: {
    webSocket: webSocketSlice,
    cascade: cascadeSlice
  },
  preloadedState: {
    webSocket: {
      isConnected: false,
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
    }
  }
});

// Test wrapper component
const createWrapper = (store = createTestStore()) => {
  return ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

// Mock WebSocketClient implementation
const createMockWebSocketClient = () => {
  const mockClient = {
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn(),
    resetReconnectAttempts: jest.fn(),
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn(),
    isConnected: jest.fn().mockReturnValue(false),
    getConfig: jest.fn().mockReturnValue({
      maxReconnectAttempts: 5,
      reconnectDelay: 1000,
      aiBufferTimeout: 500,
      maxReconnectDelay: 30000,
      heartbeatInterval: 30000
    })
  };

  (WebSocketClient as jest.MockedClass<typeof WebSocketClient>).mockImplementation(() => mockClient as any);

  return mockClient;
};

describe('useWebSocket', () => {
  let mockClient: any;
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    mockClient = createMockWebSocketClient();
    store = createTestStore();

    // Mock external services
    (webSocketAnimationService.init as jest.Mock).mockImplementation(() => {});
    (initializeWebSocketIntegration as jest.Mock).mockImplementation(() => jest.fn());
    (notificationService.initializeWebSocketListener as jest.Mock).mockImplementation(() => jest.fn());
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('useWebSocket hook initialization', () => {
    it('should establish WebSocket connection on mount with valid credentials', () => {
      const { result } = renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      expect(WebSocketClient).toHaveBeenCalledWith('test-user-123', 'test-token-abc');
      expect(mockClient.connect).toHaveBeenCalled();
      expect(result.current.isConnected).toBe(false);
    });

    it('should not create connection with missing userId', () => {
      const { result } = renderHook(
        () => useWebSocket('', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      expect(WebSocketClient).not.toHaveBeenCalled();
      expect(mockClient.connect).not.toHaveBeenCalled();
      expect(mockConsole.warn).toHaveBeenCalledWith(
        '[useWebSocket] ❌ Cannot connect - missing credentials:',
        expect.objectContaining({ hasUserId: false })
      );
    });

    it('should not create connection with missing token', () => {
      const { result } = renderHook(
        () => useWebSocket('test-user-123', ''),
        { wrapper: createWrapper(store) }
      );

      expect(WebSocketClient).not.toHaveBeenCalled();
      expect(mockClient.connect).not.toHaveBeenCalled();
      expect(mockConsole.warn).toHaveBeenCalledWith(
        '[useWebSocket] ❌ Cannot connect - missing credentials:',
        expect.objectContaining({ hasToken: false })
      );
    });

    it('should set up event listeners on WebSocket client', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      expect(mockClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('userAction', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('connected', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('disconnected', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('reconnectFailed', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('authenticationFailed', expect.any(Function));
    });

    it('should initialize external services with WebSocket client', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      expect(webSocketAnimationService.init).toHaveBeenCalledWith(mockClient);
      expect(initializeWebSocketIntegration).toHaveBeenCalledWith(mockClient);
      expect(notificationService.initializeWebSocketListener).toHaveBeenCalledWith(mockClient);
    });
  });

  describe('WebSocket message handling', () => {
    it('should receive and process WebSocket messages correctly', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      // Get the update handler
      const updateHandler = mockClient.on.mock.calls.find(call => call[0] === 'update')[1];

      const testMessage: WSMessage = {
        id: 'msg-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'create',
          data: {
            primary: { id: 'task-1', title: 'Test Task' }
          }
        },
        metadata: {
          source: 'user',
          userId: 'test-user-123'
        }
      };

      act(() => {
        updateHandler(testMessage);
      });

      // Verify message was processed
      expect(mockConsole.log).toHaveBeenCalledWith(
        '[useWebSocket] 🎯 🚨 DELETE DEBUG: UPDATE EVENT RECEIVED:',
        expect.objectContaining({
          messageId: 'msg-1',
          entity: 'task',
          action: 'create'
        })
      );
    });

    it('should handle DELETE messages with special logging', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const updateHandler = mockClient.on.mock.calls.find(call => call[0] === 'update')[1];

      const deleteMessage: WSMessage = {
        id: 'del-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'delete',
          data: {
            primary: { id: 'task-1' }
          }
        },
        metadata: {
          source: 'user',
          userId: 'test-user-123'
        }
      };

      act(() => {
        updateHandler(deleteMessage);
      });

      expect(mockConsole.warn).toHaveBeenCalledWith('🗑️ DELETE UPDATE EVENT RECEIVED IN useWebSocket HOOK:');
      expect(mockConsole.warn).toHaveBeenCalledWith('  Message ID:', 'del-1');
      expect(mockConsole.warn).toHaveBeenCalledWith('  Entity:', 'task');
      expect(mockConsole.warn).toHaveBeenCalledWith('  Action:', 'delete');
    });

    it('should process cascade data when present', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const updateHandler = mockClient.on.mock.calls.find(call => call[0] === 'update')[1];

      const cascadeMessage: WSMessage = {
        id: 'cascade-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'update',
          data: {
            primary: { id: 'task-1', title: 'Updated Task' },
            cascade: {
              tasks: [{ id: 'task-2', title: 'Related Task' }],
              branches: [{ id: 'branch-1', name: 'Feature Branch' }]
            }
          }
        },
        metadata: {
          source: 'mcp-ai'
        }
      };

      act(() => {
        updateHandler(cascadeMessage);
      });

      expect(mockConsole.log).toHaveBeenCalledWith('[useWebSocket] 🔄 Processing cascade data');
    });
  });

  describe('WebSocket connection events', () => {
    it('should handle connection success', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const connectedHandler = mockClient.on.mock.calls.find(call => call[0] === 'connected')[1];

      act(() => {
        connectedHandler();
      });

      expect(mockConsole.log).toHaveBeenCalledWith('[useWebSocket] ✅ CONNECTED - WebSocket ready');
    });

    it('should handle disconnection', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const disconnectedHandler = mockClient.on.mock.calls.find(call => call[0] === 'disconnected')[1];

      act(() => {
        disconnectedHandler();
      });

      expect(mockConsole.log).toHaveBeenCalledWith('[useWebSocket] ❌ DISCONNECTED');
    });

    it('should handle connection errors', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const errorHandler = mockClient.on.mock.calls.find(call => call[0] === 'error')[1];
      const testError = new Event('error');

      act(() => {
        errorHandler(testError);
      });

      expect(mockConsole.error).toHaveBeenCalledWith('[useWebSocket] ❌ ERROR:', testError);
    });

    it('should handle reconnection failures', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const reconnectFailedHandler = mockClient.on.mock.calls.find(call => call[0] === 'reconnectFailed')[1];

      act(() => {
        reconnectFailedHandler();
      });

      expect(mockConsole.error).toHaveBeenCalledWith('[useWebSocket] ❌ RECONNECT FAILED');
    });

    it('should handle authentication failures', () => {
      renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const authFailedHandler = mockClient.on.mock.calls.find(call => call[0] === 'authenticationFailed')[1];

      act(() => {
        authFailedHandler('Invalid token');
      });

      expect(mockConsole.error).toHaveBeenCalledWith('[useWebSocket] ❌ AUTHENTICATION FAILED:', 'Invalid token');
    });
  });

  describe('Hook API methods', () => {
    it('should provide sendMessage function', () => {
      const { result } = renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      const testMessage = { type: 'test', data: 'test data' };

      act(() => {
        result.current.sendMessage(testMessage);
      });

      expect(mockClient.send).toHaveBeenCalledWith(testMessage);
    });

    it('should provide reconnect function', () => {
      const { result } = renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      act(() => {
        result.current.reconnect();
      });

      expect(mockClient.resetReconnectAttempts).toHaveBeenCalled();
      expect(mockClient.connect).toHaveBeenCalledTimes(2); // Initial + manual reconnect
    });

    it('should provide disconnect function', () => {
      const { result } = renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      act(() => {
        result.current.disconnect();
      });

      expect(mockClient.disconnect).toHaveBeenCalled();
      expect(mockConsole.log).toHaveBeenCalledWith('[useWebSocket] Disconnecting WebSocket (explicit disconnect)');
    });

    it('should handle sendMessage when client not initialized', () => {
      // Create hook with invalid credentials to prevent client initialization
      const { result } = renderHook(
        () => useWebSocket('', ''),
        { wrapper: createWrapper(store) }
      );

      act(() => {
        result.current.sendMessage({ test: 'data' });
      });

      expect(mockConsole.error).toHaveBeenCalledWith('[useWebSocket] Client not initialized');
    });
  });

  describe('Cleanup on unmount', () => {
    it('should cleanup services on unmount but keep connection', () => {
      const mockCleanupChangePool = jest.fn();
      const mockCleanupNotifications = jest.fn();

      (initializeWebSocketIntegration as jest.Mock).mockReturnValue(mockCleanupChangePool);
      (notificationService.initializeWebSocketListener as jest.Mock).mockReturnValue(mockCleanupNotifications);

      const { unmount } = renderHook(
        () => useWebSocket('test-user-123', 'test-token-abc'),
        { wrapper: createWrapper(store) }
      );

      unmount();

      expect(mockCleanupChangePool).toHaveBeenCalled();
      expect(mockCleanupNotifications).toHaveBeenCalled();
      expect(mockClient.disconnect).not.toHaveBeenCalled(); // Should not disconnect on unmount
      expect(mockConsole.log).toHaveBeenCalledWith('[useWebSocket] Component cleanup (keeping WebSocket connected)');
    });
  });
});

describe('useBranchWebSocket', () => {
  let mockClient: any;
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    mockClient = createMockWebSocketClient();
    store = createTestStore();

    // Mock external services
    (webSocketAnimationService.init as jest.Mock).mockImplementation(() => {});
    (initializeWebSocketIntegration as jest.Mock).mockImplementation(() => jest.fn());
    (notificationService.initializeWebSocketListener as jest.Mock).mockImplementation(() => jest.fn());
  });

  it('should subscribe to branch updates when connected', () => {
    // Set up connected state
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    const { result } = renderHook(
      () => useBranchWebSocket('test-user-123', 'test-token-abc', 'branch-123'),
      { wrapper: createWrapper(store) }
    );

    // Should have called sendMessage to subscribe
    expect(mockClient.send).toHaveBeenCalledWith({
      type: 'subscribe',
      scope: 'branch',
      filters: {
        branch_id: 'branch-123'
      }
    });
  });

  it('should not subscribe without branchId', () => {
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    renderHook(
      () => useBranchWebSocket('test-user-123', 'test-token-abc'),
      { wrapper: createWrapper(store) }
    );

    expect(mockClient.send).not.toHaveBeenCalled();
  });

  it('should resubscribe when branchId changes', () => {
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    const { rerender } = renderHook(
      ({ branchId }) => useBranchWebSocket('test-user-123', 'test-token-abc', branchId),
      {
        wrapper: createWrapper(store),
        initialProps: { branchId: 'branch-123' }
      }
    );

    expect(mockClient.send).toHaveBeenCalledTimes(1);

    rerender({ branchId: 'branch-456' });

    expect(mockClient.send).toHaveBeenCalledTimes(2);
    expect(mockClient.send).toHaveBeenLastCalledWith({
      type: 'subscribe',
      scope: 'branch',
      filters: {
        branch_id: 'branch-456'
      }
    });
  });
});

describe('useTaskWebSocket', () => {
  let mockClient: any;
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    mockClient = createMockWebSocketClient();
    store = createTestStore();

    // Mock external services
    (webSocketAnimationService.init as jest.Mock).mockImplementation(() => {});
    (initializeWebSocketIntegration as jest.Mock).mockImplementation(() => jest.fn());
    (notificationService.initializeWebSocketListener as jest.Mock).mockImplementation(() => jest.fn());
  });

  it('should subscribe to task updates when connected', () => {
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    renderHook(
      () => useTaskWebSocket('test-user-123', 'test-token-abc', 'task-123'),
      { wrapper: createWrapper(store) }
    );

    expect(mockClient.send).toHaveBeenCalledWith({
      type: 'subscribe',
      scope: 'task',
      filters: {
        task_id: 'task-123'
      }
    });
  });

  it('should provide updateTask function', () => {
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    const { result } = renderHook(
      () => useTaskWebSocket('test-user-123', 'test-token-abc', 'task-123'),
      { wrapper: createWrapper(store) }
    );

    const updateData = { status: 'in_progress' };

    act(() => {
      result.current.updateTask(updateData);
    });

    expect(mockClient.send).toHaveBeenCalledWith({
      type: 'update',
      payload: {
        entity: 'task',
        action: 'update',
        data: {
          primary: { id: 'task-123', status: 'in_progress' }
        }
      },
      metadata: {
        source: 'user'
      }
    });
  });

  it('should not subscribe without taskId', () => {
    store.dispatch({ type: 'webSocket/connected', payload: {} });

    renderHook(
      () => useTaskWebSocket('test-user-123', 'test-token-abc'),
      { wrapper: createWrapper(store) }
    );

    expect(mockClient.send).not.toHaveBeenCalled();
  });
});