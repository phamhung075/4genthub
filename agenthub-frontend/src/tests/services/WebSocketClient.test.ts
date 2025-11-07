import { WebSocketClient } from '../../services/WebSocketClient';
import type { WSMessage } from '../../types/websocketTypes';
import { EventEmitter } from '../../utils/EventEmitter';

// Mock WebSocket
class MockWebSocket {
  readyState: number = WebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  
  constructor(url: string) {
    this.url = url;
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
    }
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    // Mock send implementation
  }
}

// Global WebSocket mock
(global as any).WebSocket = MockWebSocket;

// Mock timers
jest.useFakeTimers();

// Mock config
vi.mock('../../config/environment', () => ({
  config: {
    websocket: {
      url: 'ws://localhost:8000',
      maxReconnectAttempts: 5,
      reconnectDelay: 1000,
      aiBufferTimeout: 500,
      maxReconnectDelay: 30000,
      heartbeatInterval: 30000
    }
  }
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}));

import logger from '../../utils/logger';

describe('WebSocketClient', () => {
  let client: WebSocketClient;
  let mockWs: MockWebSocket;
  const token = 'test-token-abc';

  beforeEach(() => {
    vi.clearAllMocks();
    jest.clearAllTimers();
    client = new WebSocketClient(token, 'test-user-id');
  });

  afterEach(() => {
    client.disconnect();
    vi.restoreAllMocks();
    (logger.debug as any).mockClear();
    (logger.info as any).mockClear();
    (logger.warn as any).mockClear();
    (logger.error as any).mockClear();
  });

  describe('constructor', () => {
    it('should initialize with token', () => {
      expect(client).toBeInstanceOf(EventEmitter);
      expect(client).toBeDefined();
    });
  });

  describe('connect()', () => {
    beforeEach(() => {
      // Capture WebSocket instance when created
      vi.spyOn(global as any, 'WebSocket').mockImplementation((url: string) => {
        mockWs = new MockWebSocket(url);
        return mockWs;
      });
    });

    it('should create WebSocket connection with correct URL', () => {
      client.connect();
      
      expect(mockWs).toBeDefined();
      expect(mockWs.url).toBe(`ws://localhost:8000/ws/realtime?token=${token}`);
    });

    it('should handle missing WebSocket URL configuration', () => {
      // Mock config without websocket URL
      jest.resetModules();
      vi.mock('../../config/environment', () => ({
        config: {
          websocket: {
            url: '',
            maxReconnectAttempts: 5,
            reconnectDelay: 1000,
            aiBufferTimeout: 500,
            maxReconnectDelay: 30000,
            heartbeatInterval: 30000
          }
        }
      }));
      
      const errorSpy = vi.fn();
      const { WebSocketClient: WSClient } = require('../../services/WebSocketClient');
      const testClient = new WSClient(token);
      testClient.on('error', errorSpy);
      
      testClient.connect();
      
      expect(errorSpy).toHaveBeenCalledWith(new Error('WebSocket URL not configured'));
      expect(logger.error).toHaveBeenCalledWith('[WebSocket v2.0] ❌ WebSocket URL is not configured');
    });

    it('should not reconnect if already connected', () => {
      client.connect();
      const firstWs = mockWs;
      
      // Simulate open connection
      mockWs.readyState = WebSocket.OPEN;
      
      client.connect();
      
      expect(mockWs).toBe(firstWs);
    });

    it('should set up event handlers', () => {
      client.connect();
      
      expect(mockWs.onopen).toBeDefined();
      expect(mockWs.onmessage).toBeDefined();
      expect(mockWs.onerror).toBeDefined();
      expect(mockWs.onclose).toBeDefined();
    });
  });

  describe('handleOpen', () => {
    it('should emit connected event and start heartbeat', () => {
      const connectedSpy = vi.fn();
      client.on('connected', connectedSpy);
      
      client.connect();
      mockWs.readyState = WebSocket.OPEN;
      
      // Trigger open event
      const openEvent = new Event('open');
      mockWs.onopen?.(openEvent);
      
      expect(connectedSpy).toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalledWith('[WebSocket v2.0] ✅ Connected successfully');
    });
  });

  describe('handleMessage', () => {
    let updateSpy: any;
    let userActionSpy: any;

    beforeEach(() => {
      updateSpy = vi.fn();
      userActionSpy = vi.fn();
      client.on('update', updateSpy);
      client.on('userAction', userActionSpy);
      client.connect();
    });

    it('should parse and process v2.0 messages', () => {
      const message: WSMessage = {
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
          userId: 'user-1'
        }
      };

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(message)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(updateSpy).toHaveBeenCalledWith(message);
      expect(userActionSpy).toHaveBeenCalledWith(message);
    });

    it('should reject non-v2.0 messages', () => {
      const oldMessage = {
        id: 'msg-1',
        version: '1.0',
        type: 'update',
        payload: {}
      };

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(oldMessage)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(updateSpy).not.toHaveBeenCalled();
      expect(logger.error).toHaveBeenCalledWith(
        '[WebSocket] ❌ Rejected non-v2.0 message:',
        '1.0'
      );
    });

    it('should handle heartbeat messages', () => {
      const heartbeat: WSMessage = {
        id: 'hb-1',
        version: '2.0',
        type: 'heartbeat',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'system',
          action: 'ping',
          data: { primary: {} }
        },
        metadata: {
          source: 'system'
        }
      };

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(heartbeat)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(updateSpy).not.toHaveBeenCalled();
      expect(logger.debug).toHaveBeenCalledWith('[WebSocket v2.0] 💓 Heartbeat received');
    });

    it('should buffer AI updates', () => {
      const aiMessage: WSMessage = {
        id: 'ai-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'update',
          data: {
            primary: { id: 'task-1', progress: 50 }
          }
        },
        metadata: {
          source: 'mcp-ai'
        }
      };

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(aiMessage)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      // Should not emit immediately
      expect(updateSpy).not.toHaveBeenCalled();
      
      // Fast forward 500ms
      jest.advanceTimersByTime(500);
      
      // Now should emit batched update
      expect(updateSpy).toHaveBeenCalledTimes(1);
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'bulk',
          version: '2.0'
        })
      );
    });

    it('should handle delete operations with special logging', () => {
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
          userId: 'user-1'
        }
      };

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(deleteMessage)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(logger.warn).toHaveBeenCalledWith('🗑️ DELETE MESSAGE RECEIVED IN WEBSOCKET CLIENT:');
      expect(updateSpy).toHaveBeenCalledWith(deleteMessage);
    });

    it('should handle parse errors', () => {
      const messageEvent = new MessageEvent('message', {
        data: 'invalid json'
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(logger.error).toHaveBeenCalledWith(
        '[WebSocket] ❌ Failed to parse message:',
        expect.any(Error)
      );
    });
  });

  describe('mergeAIUpdates', () => {
    it('should merge and deduplicate cascade data', () => {
      client.connect();
      
      const messages: WSMessage[] = [
        {
          id: 'ai-1',
          version: '2.0',
          type: 'update',
          timestamp: new Date().toISOString(),
          sequence: 1,
          payload: {
            entity: 'task',
            action: 'update',
            data: {
              primary: { id: 'task-1' },
              cascade: {
                tasks: [{ id: 't1' }, { id: 't2' }],
                branches: [{ id: 'b1' }]
              }
            }
          },
          metadata: { source: 'mcp-ai' }
        },
        {
          id: 'ai-2',
          version: '2.0',
          type: 'update',
          timestamp: new Date().toISOString(),
          sequence: 2,
          payload: {
            entity: 'task',
            action: 'update',
            data: {
              primary: { id: 'task-2' },
              cascade: {
                tasks: [{ id: 't2' }, { id: 't3' }], // t2 is duplicate
                branches: [{ id: 'b2' }]
              }
            }
          },
          metadata: { source: 'mcp-ai' }
        }
      ];

      // Send messages
      messages.forEach(msg => {
        const messageEvent = new MessageEvent('message', {
          data: JSON.stringify(msg)
        });
        mockWs.onmessage?.(messageEvent);
      });

      const updateSpy = vi.fn();
      client.on('update', updateSpy);

      // Fast forward to process batch
      jest.advanceTimersByTime(500);

      const mergedUpdate = updateSpy.mock.calls[0][0];
      
      expect(mergedUpdate.type).toBe('bulk');
      expect(mergedUpdate.payload.data.primary).toHaveLength(2);
      expect(mergedUpdate.payload.data.cascade.tasks).toHaveLength(3); // Deduplicated
      expect(mergedUpdate.payload.data.cascade.branches).toHaveLength(2);
    });
  });

  describe('send', () => {
    beforeEach(() => {
      client.connect();
      mockWs.readyState = WebSocket.OPEN;
      mockWs.send = vi.fn();
    });

    it('should send v2.0 formatted message', () => {
      const message = {
        type: 'update',
        payload: {
          entity: 'task',
          action: 'create',
          data: { primary: { title: 'Test' } }
        }
      };

      client.send(message);

      const sentMessage = JSON.parse((mockWs.send as any).mock.calls[0][0]);
      
      expect(sentMessage).toMatchObject({
        version: '2.0',
        type: 'update',
        payload: message.payload
      });
      expect(sentMessage.id).toMatch(/^msg-\d+$/);
      expect(sentMessage.timestamp).toBeDefined();
      expect(sentMessage.sequence).toBe(0);
    });

    it('should not send if not connected', () => {
      mockWs.readyState = WebSocket.CLOSED;
      
      client.send({ type: 'update' });
      
      expect(mockWs.send).not.toHaveBeenCalled();
      expect(logger.error).toHaveBeenCalledWith('[WebSocket] Not connected');
    });
  });

  describe('handleError', () => {
    it('should emit error event', () => {
      const errorSpy = vi.fn();
      client.on('error', errorSpy);
      
      client.connect();
      
      const error = new Event('error');
      mockWs.onerror?.(error);
      
      expect(errorSpy).toHaveBeenCalledWith(error);
      expect(logger.error).toHaveBeenCalledWith('[WebSocket v2.0] ❌ Connection error:', error);
    });
  });

  describe('handleClose', () => {
    beforeEach(() => {
      client.connect();
    });

    it('should attempt reconnection on normal close', () => {
      const closeEvent = new CloseEvent('close', {
        code: 1006,
        reason: 'Connection lost'
      });
      
      mockWs.onclose?.(closeEvent);
      
      // Should schedule reconnect
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 1000);
      
      // Fast forward and check reconnection
      jest.advanceTimersByTime(1000);
      
      // Should create new WebSocket
      expect(WebSocket).toHaveBeenCalledTimes(2);
    });

    it('should not reconnect on authentication failure', () => {
      const authFailureSpy = vi.fn();
      client.on('authenticationFailed', authFailureSpy);
      
      const closeEvent = new CloseEvent('close', {
        code: 1008,
        reason: 'Invalid token'
      });
      
      mockWs.onclose?.(closeEvent);
      
      expect(authFailureSpy).toHaveBeenCalledWith('Invalid token');
      expect(setTimeout).not.toHaveBeenCalled();
    });

    it('should use exponential backoff for reconnections', () => {
      // First reconnect
      mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 1000);
      
      jest.advanceTimersByTime(1000);
      
      // Second reconnect
      mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 2000);
      
      jest.advanceTimersByTime(2000);
      
      // Third reconnect
      mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 4000);
    });

    it('should emit reconnectFailed after max attempts', () => {
      const reconnectFailedSpy = vi.fn();
      client.on('reconnectFailed', reconnectFailedSpy);
      
      // Simulate max reconnection attempts
      for (let i = 0; i < 5; i++) {
        mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
        jest.advanceTimersByTime(30000);
      }
      
      // Should not schedule another reconnect
      mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
      
      expect(reconnectFailedSpy).toHaveBeenCalled();
      expect(logger.error).toHaveBeenCalledWith('[WebSocket] Max reconnection attempts reached');
    });
  });

  describe('heartbeat', () => {
    beforeEach(() => {
      client.connect();
      mockWs.readyState = WebSocket.OPEN;
      mockWs.send = vi.fn();
    });

    it('should send heartbeat every 30 seconds', () => {
      // Trigger connection open
      mockWs.onopen?.(new Event('open'));
      
      // Fast forward 30 seconds
      jest.advanceTimersByTime(30000);
      
      const sentMessage = JSON.parse((mockWs.send as any).mock.calls[0][0]);
      
      expect(sentMessage).toMatchObject({
        type: 'heartbeat',
        payload: {
          entity: 'system',
          action: 'ping'
        }
      });
    });

    it('should stop heartbeat on disconnect', () => {
      mockWs.onopen?.(new Event('open'));
      
      client.disconnect();
      
      // Fast forward 30 seconds
      jest.advanceTimersByTime(30000);
      
      // Should not send heartbeat
      expect(mockWs.send).not.toHaveBeenCalled();
    });
  });

  describe('disconnect', () => {
    it('should close connection and cleanup', () => {
      client.connect();
      mockWs.readyState = WebSocket.OPEN;
      
      client.disconnect();
      
      expect(mockWs.readyState).toBe(WebSocket.CLOSED);
    });

    it('should clear AI buffer and timers', () => {
      client.connect();
      
      // Send an AI message to create buffer timer
      const aiMessage: WSMessage = {
        id: 'ai-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'update',
          data: { primary: {} }
        },
        metadata: { source: 'mcp-ai' }
      };
      
      mockWs.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(aiMessage)
      }));
      
      client.disconnect();
      
      // Fast forward - should not process batch
      jest.advanceTimersByTime(500);
      
      const updateSpy = vi.fn();
      client.on('update', updateSpy);
      expect(updateSpy).not.toHaveBeenCalled();
    });
  });

  describe('isConnected', () => {
    it('should return false when not connected', () => {
      expect(client.isConnected()).toBe(false);
    });

    it('should return true when connected', () => {
      client.connect();
      mockWs.readyState = WebSocket.OPEN;
      
      expect(client.isConnected()).toBe(true);
    });

    it('should return false when connecting', () => {
      client.connect();
      mockWs.readyState = WebSocket.CONNECTING;
      
      expect(client.isConnected()).toBe(false);
    });
  });

  describe('resetReconnectAttempts', () => {
    it('should reset reconnection counter', () => {
      client.connect();
      
      // Trigger a few failed reconnections
      for (let i = 0; i < 3; i++) {
        mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
        jest.advanceTimersByTime(10000);
      }
      
      client.resetReconnectAttempts();
      
      // Should start from 1000ms delay again
      mockWs.onclose?.(new CloseEvent('close', { code: 1006 }));
      expect(setTimeout).toHaveBeenLastCalledWith(expect.any(Function), 1000);
    });
  });
});