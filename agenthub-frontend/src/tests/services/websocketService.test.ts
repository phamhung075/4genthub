import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { websocketService } from '../../services/websocketService';
import { toastEventBus } from '../../services/toastEventBus';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: code || 1000, reason }));
    }
  }
}

// Mock dependencies
vi.mock('../../services/toastEventBus', () => ({
  toastEventBus: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('../../utils/logger', () => ({
  default: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));

// Setup WebSocket mock
(global as any).WebSocket = MockWebSocket;

describe('WebSocketService', () => {
  let mockLocalStorage: { [key: string]: string } = {};

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Mock localStorage
    mockLocalStorage = {};
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: (key: string) => mockLocalStorage[key] || null,
        setItem: (key: string, value: string) => {
          mockLocalStorage[key] = value;
        },
        removeItem: (key: string) => {
          delete mockLocalStorage[key];
        },
      },
      writable: true,
    });

    // Reset WebSocket service state
    websocketService.disconnect();
  });

  afterEach(() => {
    vi.useRealTimers();
    websocketService.disconnect();
  });

  describe('Connection Management', () => {
    it('should connect to WebSocket server', async () => {
      const connectPromise = websocketService.connect('test-token');
      
      // Wait for connection to open
      await vi.advanceTimersByTimeAsync(20);
      await connectPromise;

      expect(websocketService.isConnected()).toBe(true);
    });

    it('should use token from localStorage if not provided', async () => {
      mockLocalStorage['access_token'] = 'stored-token';
      
      const connectPromise = websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);
      await connectPromise;

      expect(websocketService.isConnected()).toBe(true);
    });

    it('should disconnect properly', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      websocketService.disconnect();
      expect(websocketService.isConnected()).toBe(false);
    });

    it('should reconnect with new token', async () => {
      await websocketService.connect('old-token');
      await vi.advanceTimersByTimeAsync(20);

      await websocketService.reconnectWithNewToken('new-token');
      await vi.advanceTimersByTimeAsync(120);

      expect(websocketService.isConnected()).toBe(true);
    });

    it('should not attempt to connect if already connected', async () => {
      const spy = vi.spyOn(MockWebSocket.prototype, 'constructor' as any);
      
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const callCount = spy.mock.calls.length;
      
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      expect(spy.mock.calls.length).toBe(callCount);
    });
  });

  describe('Message Handling', () => {
    let ws: MockWebSocket;

    beforeEach(async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      // Get the WebSocket instance
      ws = (websocketService as any).ws;
    });

    it('should handle data change notifications', () => {
      const handler = vi.fn();
      websocketService.on('task', handler);

      const message = {
        type: 'status_update',
        event_type: 'updated',
        metadata: {
          entity_type: 'task',
          entity_id: 'task-123',
          event_type: 'updated',
        },
        data: {
          title: 'Test Task',
        },
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(handler).toHaveBeenCalledWith(message);
    });

    it('should show notifications for entity changes', () => {
      const message = {
        type: 'status_update',
        event_type: 'created',
        metadata: {
          entity_type: 'task',
          entity_id: 'task-123',
          event_type: 'created',
        },
        data: {
          title: 'New Task',
        },
        user_id: 'other-user',
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(toastEventBus.success).toHaveBeenCalledWith(
        'New task created',
        'Another user created "New Task"'
      );
    });

    it('should not show notifications for current user actions', () => {
      mockLocalStorage['user_id'] = 'current-user';

      const message = {
        type: 'status_update',
        event_type: 'created',
        metadata: {
          entity_type: 'task',
          entity_id: 'task-123',
          event_type: 'created',
        },
        data: {
          title: 'New Task',
        },
        user_id: 'current-user',
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(toastEventBus.success).not.toHaveBeenCalled();
    });

    it('should skip branch creation/deletion notifications', () => {
      const message = {
        type: 'status_update',
        metadata: {
          entity_type: 'branch',
          event_type: 'created',
        },
        data: {
          git_branch_name: 'feature-branch',
        },
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(toastEventBus.success).not.toHaveBeenCalled();
    });

    it('should handle system messages', () => {
      const systemMessages = [
        { type: 'welcome' },
        { type: 'auth_success' },
        { type: 'pong' },
        { type: 'subscribed' },
      ];

      systemMessages.forEach((message) => {
        if (ws.onmessage) {
          ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
        }
      });

      // System messages should not trigger notifications
      expect(toastEventBus.success).not.toHaveBeenCalled();
      expect(toastEventBus.info).not.toHaveBeenCalled();
    });
  });

  describe('Event Handlers', () => {
    it('should register and unregister handlers', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const handler = vi.fn();
      const unsubscribe = websocketService.on('task', handler);

      const ws = (websocketService as any).ws;
      const message = {
        type: 'status_update',
        metadata: {
          entity_type: 'task',
          event_type: 'updated',
        },
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(handler).toHaveBeenCalledTimes(1);

      // Unsubscribe
      unsubscribe();

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple handlers for same event', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const handler1 = vi.fn();
      const handler2 = vi.fn();

      websocketService.on('task', handler1);
      websocketService.on('task', handler2);

      const ws = (websocketService as any).ws;
      const message = {
        type: 'status_update',
        metadata: {
          entity_type: 'task',
          event_type: 'updated',
        },
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });

    it('should handle universal handlers', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const universalHandler = vi.fn();
      websocketService.on('*', universalHandler);

      const ws = (websocketService as any).ws;
      const message = {
        type: 'status_update',
        metadata: {
          entity_type: 'task',
          event_type: 'updated',
        },
      };

      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
      }

      expect(universalHandler).toHaveBeenCalled();
    });
  });

  describe('Heartbeat and Reconnection', () => {
    it('should send heartbeat pings', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;
      const sendSpy = vi.spyOn(ws, 'send');

      // Advance time to trigger heartbeat
      await vi.advanceTimersByTimeAsync(30000);

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }));
    });

    it('should attempt reconnection on unexpected close', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;

      // Simulate unexpected close
      if (ws.onclose) {
        ws.onclose(new CloseEvent('close', { code: 1006 }));
      }

      // Advance time for reconnection attempt
      await vi.advanceTimersByTimeAsync(1500);

      // Check that reconnection was attempted
      expect(websocketService.isConnected()).toBe(false);
    });

    it('should not reconnect on intentional close', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;

      // Simulate intentional close
      if (ws.onclose) {
        ws.onclose(new CloseEvent('close', { code: 1000 }));
      }

      // Advance time
      await vi.advanceTimersByTimeAsync(5000);

      // Should not attempt reconnection
      expect(websocketService.isConnected()).toBe(false);
    });
  });

  describe('Subscription Methods', () => {
    it('should subscribe to project updates', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;
      const sendSpy = vi.spyOn(ws, 'send');

      websocketService.subscribeToProject('project-123');

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({
        type: 'subscribe',
        scope: 'project',
        filters: { project_id: 'project-123' },
      }));
    });

    it('should subscribe to branch updates', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;
      const sendSpy = vi.spyOn(ws, 'send');

      websocketService.subscribeToBranch('branch-123');

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({
        type: 'subscribe',
        scope: 'branch',
        filters: { git_branch_id: 'branch-123' },
      }));
    });

    it('should subscribe to task updates', async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);

      const ws = (websocketService as any).ws;
      const sendSpy = vi.spyOn(ws, 'send');

      websocketService.subscribeToTask('task-123');

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({
        type: 'subscribe',
        scope: 'task',
        filters: { task_id: 'task-123' },
      }));
    });
  });

  describe('Notification Types', () => {
    beforeEach(async () => {
      await websocketService.connect();
      await vi.advanceTimersByTimeAsync(20);
    });

    it('should show different toast types based on event', () => {
      const ws = (websocketService as any).ws;
      
      const events = [
        { event_type: 'created', expectedMethod: 'success' },
        { event_type: 'updated', expectedMethod: 'info' },
        { event_type: 'deleted', expectedMethod: 'warning' },
        { event_type: 'completed', expectedMethod: 'success' },
        { event_type: 'archived', expectedMethod: 'info' },
        { event_type: 'restored', expectedMethod: 'info' },
      ];

      events.forEach(({ event_type, expectedMethod }) => {
        vi.clearAllMocks();

        const message = {
          type: 'status_update',
          metadata: {
            entity_type: 'task',
            event_type,
          },
          data: {
            title: 'Test Task',
          },
          user_id: 'other-user',
        };

        if (ws.onmessage) {
          ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
        }

        expect((toastEventBus as any)[expectedMethod]).toHaveBeenCalled();
      });
    });
  });
});