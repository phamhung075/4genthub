import { testWebSocketConnection } from '../../utils/testWebSocket';

// Mock WebSocket
class MockWebSocket {
  readyState: number = WebSocket.CONNECTING;
  url: string;
  protocol: string = '';
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  
  constructor(url: string) {
    this.url = url;
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    // Mock send implementation
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
  }
}

// Global WebSocket mock
(global as any).WebSocket = MockWebSocket;

// Mock console methods
const consoleSpy = {
  log: jest.spyOn(console, 'log').mockImplementation(),
  error: jest.spyOn(console, 'error').mockImplementation(),
};

// Mock environment
const mockEnv = {
  VITE_BACKEND_URL: ''
};

Object.defineProperty(import.meta, 'env', {
  get: () => mockEnv,
  configurable: true
});

describe('testWebSocketConnection', () => {
  let mockWs: MockWebSocket;
  const userId = 'test-user-123';
  const token = 'test-token-abcdefghijklmnopqrstuvwxyz';

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset environment
    mockEnv.VITE_BACKEND_URL = '';
    
    // Capture WebSocket instance when created
    jest.spyOn(global as any, 'WebSocket').mockImplementation((url: string) => {
      mockWs = new MockWebSocket(url);
      return mockWs;
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('URL construction', () => {
    it('should use default localhost URL when no backend URL provided', () => {
      const ws = testWebSocketConnection(userId, token);
      
      expect(mockWs.url).toBe(`ws://localhost:8000/ws/realtime?token=${token}`);
      expect(consoleSpy.log).toHaveBeenCalledWith('Backend URL:', 'Using default');
    });

    it('should use provided backend URL', () => {
      const ws = testWebSocketConnection(userId, token, 'http://custom.backend.com:3000');
      
      expect(mockWs.url).toBe(`ws://custom.backend.com:3000/ws/realtime?token=${token}`);
      expect(consoleSpy.log).toHaveBeenCalledWith('Backend URL:', 'http://custom.backend.com:3000');
    });

    it('should use WSS for HTTPS backend URLs', () => {
      const ws = testWebSocketConnection(userId, token, 'https://secure.backend.com');
      
      expect(mockWs.url).toBe(`wss://secure.backend.com/ws/realtime?token=${token}`);
    });

    it('should use VITE_BACKEND_URL from environment', () => {
      mockEnv.VITE_BACKEND_URL = 'http://env.backend.com:4000';
      
      const ws = testWebSocketConnection(userId, token);
      
      expect(mockWs.url).toBe(`ws://env.backend.com:4000/ws/realtime?token=${token}`);
    });

    it('should prioritize provided backend URL over environment', () => {
      mockEnv.VITE_BACKEND_URL = 'http://env.backend.com:4000';
      
      const ws = testWebSocketConnection(userId, token, 'http://provided.backend.com:5000');
      
      expect(mockWs.url).toBe(`ws://provided.backend.com:5000/ws/realtime?token=${token}`);
    });
  });

  describe('logging', () => {
    it('should log connection parameters', () => {
      testWebSocketConnection(userId, token);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('=== WebSocket Connection Test ===');
      expect(consoleSpy.log).toHaveBeenCalledWith('User ID:', userId);
      expect(consoleSpy.log).toHaveBeenCalledWith('Token (first 20 chars):', 'test-token-abcdefghi...');
      expect(consoleSpy.log).toHaveBeenCalledWith(
        'Attempting connection to:', 
        'ws://localhost:8000/ws/realtime?token=***'
      );
    });

    it('should handle undefined token', () => {
      testWebSocketConnection(userId, undefined as any);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('Token (first 20 chars):', '...');
    });
  });

  describe('onopen handler', () => {
    it('should log successful connection and send test message', () => {
      const ws = testWebSocketConnection(userId, token);
      
      // Mock WebSocket state
      mockWs.readyState = WebSocket.OPEN;
      mockWs.protocol = 'ws';
      mockWs.send = jest.fn();
      
      // Trigger open event
      const openEvent = new Event('open');
      mockWs.onopen?.(openEvent);
      
      // Check connection logs
      expect(consoleSpy.log).toHaveBeenCalledWith('✅ WebSocket Connected Successfully!');
      expect(consoleSpy.log).toHaveBeenCalledWith('Ready State:', WebSocket.OPEN);
      expect(consoleSpy.log).toHaveBeenCalledWith('Protocol:', 'ws');
      expect(consoleSpy.log).toHaveBeenCalledWith('URL:', expect.stringContaining('token=***'));
      
      // Check test message sent
      const sentData = (mockWs.send as jest.Mock).mock.calls[0][0];
      const sentMessage = JSON.parse(sentData);
      
      expect(sentMessage).toMatchObject({
        version: '2.0',
        type: 'heartbeat',
        payload: {
          entity: 'system',
          action: 'ping',
          data: {
            primary: { test: true }
          }
        },
        metadata: {
          source: 'test'
        }
      });
      
      expect(sentMessage.id).toMatch(/^test-\d+$/);
      expect(sentMessage.timestamp).toBeDefined();
      expect(sentMessage.sequence).toBe(0);
    });
  });

  describe('onmessage handler', () => {
    it('should parse and log JSON messages', () => {
      const ws = testWebSocketConnection(userId, token);
      
      const testMessage = {
        id: 'msg-123',
        type: 'update',
        data: { test: true }
      };
      
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(testMessage)
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('📨 Message received:', JSON.stringify(testMessage));
      expect(consoleSpy.log).toHaveBeenCalledWith('Parsed message:', testMessage);
    });

    it('should handle non-JSON messages', () => {
      const ws = testWebSocketConnection(userId, token);
      
      const messageEvent = new MessageEvent('message', {
        data: 'plain text message'
      });
      
      mockWs.onmessage?.(messageEvent);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('📨 Message received:', 'plain text message');
      expect(consoleSpy.log).toHaveBeenCalledWith('Raw message (not JSON):', 'plain text message');
    });
  });

  describe('onerror handler', () => {
    it('should log error details', () => {
      const ws = testWebSocketConnection(userId, token);
      
      mockWs.readyState = WebSocket.CLOSED;
      
      const errorEvent = new Event('error');
      mockWs.onerror?.(errorEvent);
      
      expect(consoleSpy.error).toHaveBeenCalledWith('❌ WebSocket Error:', errorEvent);
      expect(consoleSpy.error).toHaveBeenCalledWith('Ready State:', WebSocket.CLOSED);
      expect(consoleSpy.error).toHaveBeenCalledWith('URL:', expect.stringContaining('token=***'));
    });
  });

  describe('onclose handler', () => {
    it('should log close event details with normal closure', () => {
      const ws = testWebSocketConnection(userId, token);
      
      const closeEvent = new CloseEvent('close', {
        code: 1000,
        reason: 'Normal closure',
        wasClean: true
      });
      
      mockWs.onclose?.(closeEvent);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('🔌 WebSocket Closed');
      expect(consoleSpy.log).toHaveBeenCalledWith('Code:', 1000);
      expect(consoleSpy.log).toHaveBeenCalledWith('Reason:', 'Normal closure');
      expect(consoleSpy.log).toHaveBeenCalledWith('Was Clean:', true);
      expect(consoleSpy.log).toHaveBeenCalledWith('Normal closure');
    });

    it('should interpret close codes correctly', () => {
      const testCases = [
        { code: 1001, message: 'Going away (page navigation)' },
        { code: 1006, message: 'Abnormal closure - Connection lost' },
        { code: 1008, message: 'Policy violation - likely authentication issue' },
        { code: 4001, message: 'Application error - check authentication and permissions' },
      ];

      testCases.forEach(({ code, message }) => {
        const ws = testWebSocketConnection(userId, token);
        
        const closeEvent = new CloseEvent('close', {
          code,
          reason: '',
          wasClean: false
        });
        
        mockWs.onclose?.(closeEvent);
        
        expect(consoleSpy.log).toHaveBeenCalledWith(message);
      });
    });

    it('should handle close event without reason', () => {
      const ws = testWebSocketConnection(userId, token);
      
      const closeEvent = new CloseEvent('close', {
        code: 1006,
        wasClean: false
      });
      
      mockWs.onclose?.(closeEvent);
      
      expect(consoleSpy.log).toHaveBeenCalledWith('Reason:', 'No reason provided');
    });
  });

  describe('window integration', () => {
    it('should attach test function to window object', () => {
      expect((window as any).testWebSocket).toBe(testWebSocketConnection);
      expect(consoleSpy.log).toHaveBeenCalledWith(
        'WebSocket test utility loaded. Use window.testWebSocket(userId, token) to test connection.'
      );
    });

    it('should not attach to window in non-browser environment', () => {
      // Save original window
      const originalWindow = global.window;
      
      // Remove window
      delete (global as any).window;
      
      // Clear previous module cache and re-import
      jest.resetModules();
      
      // Re-import should not throw
      expect(() => require('../../utils/testWebSocket')).not.toThrow();
      
      // Restore window
      global.window = originalWindow;
    });
  });

  describe('return value', () => {
    it('should return the WebSocket instance', () => {
      const ws = testWebSocketConnection(userId, token);
      
      expect(ws).toBe(mockWs);
      expect(ws).toBeInstanceOf(MockWebSocket);
    });
  });
});