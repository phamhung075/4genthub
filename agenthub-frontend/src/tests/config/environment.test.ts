import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock import.meta.env
vi.mock('import.meta.env', () => ({
  env: {
    VITE_API_URL: 'http://localhost:8000',
    VITE_ENV: 'test',
    VITE_DEBUG: 'false',
    VITE_APP_NAME: 'agenthub',
    VITE_KEYCLOAK_URL: 'http://keycloak:8080',
    VITE_KEYCLOAK_REALM: 'agenthub',
    VITE_KEYCLOAK_CLIENT_ID: 'agenthub-frontend',
    VITE_WS_URL: '',
    VITE_WS_MAX_RECONNECT_ATTEMPTS: '5',
    VITE_WS_RECONNECT_DELAY: '1000',
    VITE_WS_AI_BUFFER_TIMEOUT: '500',
    VITE_WS_MAX_RECONNECT_DELAY: '30000',
    VITE_WS_HEARTBEAT_INTERVAL: '30000',
  }
}));

describe('environment', () => {
  let originalWindow: typeof globalThis.window;
  let originalConsoleError: typeof console.error;
  let originalConsoleWarn: typeof console.warn;
  let originalConsoleInfo: typeof console.info;
  let consoleErrorSpy: ReturnType<typeof vi.fn>;
  let consoleWarnSpy: ReturnType<typeof vi.fn>;
  let consoleInfoSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    originalWindow = global.window;
    originalConsoleError = console.error;
    originalConsoleWarn = console.warn;
    originalConsoleInfo = console.info;
    consoleErrorSpy = vi.fn();
    consoleWarnSpy = vi.fn();
    consoleInfoSpy = vi.fn();
    console.error = consoleErrorSpy;
    console.warn = consoleWarnSpy;
    console.info = consoleInfoSpy;

    // Reset window._env_
    (global as any).window = {
      location: {
        protocol: 'http:',
      },
      _env_: {},
    };

    // Clear module cache
    vi.resetModules();
  });

  afterEach(() => {
    global.window = originalWindow;
    console.error = originalConsoleError;
    console.warn = originalConsoleWarn;
    console.info = originalConsoleInfo;
    vi.clearAllMocks();
  });

  describe('getEnvVar', () => {
    it('should prefer runtime config over build-time config', async () => {
      (global as any).window._env_ = {
        VITE_API_URL: 'http://runtime-api:8000',
      };

      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('http://runtime-api:8000');
    });

    it('should use build-time value when runtime config is not available', async () => {
      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should ignore placeholder values', async () => {
      (global as any).window._env_ = {
        VITE_API_URL: '__API_URL__',
      };

      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should use default value when neither runtime nor build-time value exists', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {}
      }));

      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });
  });

  describe('API_BASE_URL', () => {
    it('should upgrade HTTP to HTTPS when page is served over HTTPS', async () => {
      (global as any).window.location.protocol = 'https:';
      
      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('https://localhost:8000');
    });

    it('should keep HTTP when page is served over HTTP', async () => {
      (global as any).window.location.protocol = 'http:';
      
      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should not modify HTTPS URLs', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_API_URL: 'https://api.example.com',
        }
      }));
      (global as any).window.location.protocol = 'https:';
      
      const { API_BASE_URL } = await import('../../config/environment');
      expect(API_BASE_URL).toBe('https://api.example.com');
    });
  });

  describe('Environment flags', () => {
    it('should correctly set environment flags for development', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'development',
        }
      }));

      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await import('../../config/environment');
      expect(ENVIRONMENT).toBe('development');
      expect(IS_DEVELOPMENT).toBe(true);
      expect(IS_PRODUCTION).toBe(false);
      expect(IS_STAGING).toBe(false);
    });

    it('should correctly set environment flags for production', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'https://api.example.com',
        }
      }));

      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await import('../../config/environment');
      expect(ENVIRONMENT).toBe('production');
      expect(IS_DEVELOPMENT).toBe(false);
      expect(IS_PRODUCTION).toBe(true);
      expect(IS_STAGING).toBe(false);
    });

    it('should correctly set environment flags for staging', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'staging',
        }
      }));

      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await import('../../config/environment');
      expect(ENVIRONMENT).toBe('staging');
      expect(IS_DEVELOPMENT).toBe(false);
      expect(IS_PRODUCTION).toBe(false);
      expect(IS_STAGING).toBe(true);
    });
  });

  describe('Debug mode', () => {
    it('should enable debug mode when VITE_DEBUG is true', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_DEBUG: 'true',
        }
      }));

      const { DEBUG_MODE } = await import('../../config/environment');
      expect(DEBUG_MODE).toBe(true);
    });

    it('should disable debug mode when VITE_DEBUG is false', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_DEBUG: 'false',
        }
      }));

      const { DEBUG_MODE } = await import('../../config/environment');
      expect(DEBUG_MODE).toBe(false);
    });

    it('should disable debug mode when VITE_DEBUG is not set', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {}
      }));

      const { DEBUG_MODE } = await import('../../config/environment');
      expect(DEBUG_MODE).toBe(false);
    });
  });

  describe('WebSocket configuration', () => {
    it('should auto-derive WebSocket URL from API URL in development', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'development',
          VITE_API_URL: 'http://localhost:8000',
        }
      }));

      const { WS_URL } = await import('../../config/environment');
      expect(WS_URL).toBe('ws://localhost:8000');
    });

    it('should auto-derive WebSocket URL from HTTPS API URL in development', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'development',
          VITE_API_URL: 'https://localhost:8000',
        }
      }));

      const { WS_URL } = await import('../../config/environment');
      expect(WS_URL).toBe('ws://localhost:8000');
    });

    it('should use explicit WebSocket URL when provided', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'development',
          VITE_API_URL: 'http://localhost:8000',
          VITE_WS_URL: 'ws://custom-ws:8001',
        }
      }));

      const { WS_URL } = await import('../../config/environment');
      expect(WS_URL).toBe('ws://custom-ws:8001');
    });

    it('should not auto-derive WebSocket URL in production', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'https://api.example.com',
        }
      }));

      const { WS_URL } = await import('../../config/environment');
      expect(WS_URL).toBe('');
    });

    it('should parse WebSocket numeric configuration correctly', async () => {
      const { 
        WS_MAX_RECONNECT_ATTEMPTS,
        WS_RECONNECT_DELAY,
        WS_AI_BUFFER_TIMEOUT,
        WS_MAX_RECONNECT_DELAY,
        WS_HEARTBEAT_INTERVAL
      } = await import('../../config/environment');

      expect(WS_MAX_RECONNECT_ATTEMPTS).toBe(5);
      expect(WS_RECONNECT_DELAY).toBe(1000);
      expect(WS_AI_BUFFER_TIMEOUT).toBe(500);
      expect(WS_MAX_RECONNECT_DELAY).toBe(30000);
      expect(WS_HEARTBEAT_INTERVAL).toBe(30000);
    });
  });

  describe('Production validation', () => {
    it('should log error when VITE_API_URL is not configured in production', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
        }
      }));

      await import('../../config/environment');
      expect(consoleErrorSpy).toHaveBeenCalledWith('CRITICAL: VITE_API_URL is not configured in production!');
      expect(consoleErrorSpy).toHaveBeenCalledWith('Please configure VITE_API_URL in CapRover environment variables');
    });

    it('should warn when API_BASE_URL contains localhost in production', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'http://localhost:8000',
        }
      }));

      await import('../../config/environment');
      expect(consoleWarnSpy).toHaveBeenCalledWith('WARNING: API_BASE_URL contains localhost in production environment');
    });

    it('should not log warnings in production with proper configuration', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'https://api.example.com',
        }
      }));

      await import('../../config/environment');
      expect(consoleErrorSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });
  });

  describe('Debug logging', () => {
    it('should log configuration in development mode', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'development',
          VITE_API_URL: 'http://localhost:8000',
          VITE_DEBUG: 'false',
        }
      }));

      await import('../../config/environment');
      expect(consoleInfoSpy).toHaveBeenCalled();
      const calls = consoleInfoSpy.mock.calls.map(call => call[0]);
      expect(calls).toContain('🔧 DEBUG: Environment Configuration Analysis:');
    });

    it('should log configuration in debug mode regardless of environment', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'https://api.example.com',
          VITE_DEBUG: 'true',
        }
      }));

      await import('../../config/environment');
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should not log configuration in production without debug mode', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_ENV: 'production',
          VITE_API_URL: 'https://api.example.com',
          VITE_DEBUG: 'false',
        }
      }));

      await import('../../config/environment');
      // Only production validation messages, no debug messages
      const infoCallsWithDebug = consoleInfoSpy.mock.calls.filter(call => 
        call[0].includes('DEBUG') || call[0].includes('🔧')
      );
      expect(infoCallsWithDebug).toHaveLength(0);
    });
  });

  describe('config object', () => {
    it('should export a config object with all settings', async () => {
      vi.resetModules();
      vi.mock('import.meta.env', () => ({
        env: {
          VITE_API_URL: 'http://localhost:8000',
          VITE_ENV: 'test',
          VITE_APP_NAME: 'agenthub-test',
          VITE_WS_URL: 'ws://test-ws:8001',
          VITE_WS_MAX_RECONNECT_ATTEMPTS: '3',
          VITE_WS_RECONNECT_DELAY: '2000',
          VITE_WS_AI_BUFFER_TIMEOUT: '1000',
          VITE_WS_MAX_RECONNECT_DELAY: '60000',
          VITE_WS_HEARTBEAT_INTERVAL: '45000',
          VITE_DEBUG: 'true',
        }
      }));

      const { config } = await import('../../config/environment');
      
      expect(config).toEqual({
        api: {
          baseUrl: 'http://localhost:8000',
          timeout: 30000,
        },
        websocket: {
          url: 'ws://test-ws:8001',
          maxReconnectAttempts: 3,
          reconnectDelay: 2000,
          aiBufferTimeout: 1000,
          maxReconnectDelay: 60000,
          heartbeatInterval: 45000,
        },
        app: {
          name: 'agenthub-test',
          environment: 'test',
        },
        debug: true,
      });
    });
  });
});