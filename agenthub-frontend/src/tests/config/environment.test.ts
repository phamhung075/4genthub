import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest';

// Every VITE_* variable environment.ts reads, cleared before each case so a
// developer .env file cannot leak values into these tests.
const ENV_KEYS = [
  'VITE_API_URL',
  'VITE_ENV',
  'VITE_DEBUG',
  'VITE_DISABLE_AUTH',
  'VITE_ENABLE_MARKETPLACE',
  'VITE_APP_NAME',
  'VITE_WS_URL',
  'VITE_WS_MAX_RECONNECT_ATTEMPTS',
  'VITE_WS_RECONNECT_DELAY',
  'VITE_WS_AI_BUFFER_TIMEOUT',
  'VITE_WS_MAX_RECONNECT_DELAY',
  'VITE_WS_HEARTBEAT_INTERVAL',
];

// environment.ts evaluates its module-level constants at load, so each case stubs
// its variables, resets the module cache and imports a fresh copy.
const loadEnvironment = async (env: Record<string, string> = {}) => {
  Object.entries(env).forEach(([key, value]) => vi.stubEnv(key, value));
  vi.resetModules();
  return import('../../config/environment');
};

describe('environment', () => {
  let windowStub: { location: { protocol: string }; _env_: Record<string, string> };
  let consoleErrorSpy: MockInstance;
  let consoleWarnSpy: MockInstance;
  let consoleInfoSpy: MockInstance;

  beforeEach(() => {
    ENV_KEYS.forEach(key => vi.stubEnv(key, undefined as unknown as string));

    windowStub = {
      location: { protocol: 'http:' },
      _env_: {},
    };
    vi.stubGlobal('window', windowStub);

    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe('getEnvVar', () => {
    it('should prefer runtime config over build-time config', async () => {
      windowStub._env_.VITE_API_URL = 'http://runtime-api:8000';

      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'http://localhost:8000' });
      expect(API_BASE_URL).toBe('http://runtime-api:8000');
    });

    it('should use build-time value when runtime config is not available', async () => {
      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'http://localhost:8000' });
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should ignore placeholder values', async () => {
      windowStub._env_.VITE_API_URL = '__API_URL__';

      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'http://localhost:8000' });
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should use default value when neither runtime nor build-time value exists', async () => {
      const { API_BASE_URL } = await loadEnvironment();
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });
  });

  describe('API_BASE_URL', () => {
    it('should upgrade HTTP to HTTPS when page is served over HTTPS', async () => {
      windowStub.location.protocol = 'https:';

      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'http://localhost:8000' });
      expect(API_BASE_URL).toBe('https://localhost:8000');
    });

    it('should keep HTTP when page is served over HTTP', async () => {
      windowStub.location.protocol = 'http:';

      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'http://localhost:8000' });
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });

    it('should not modify HTTPS URLs', async () => {
      windowStub.location.protocol = 'https:';

      const { API_BASE_URL } = await loadEnvironment({ VITE_API_URL: 'https://api.example.com' });
      expect(API_BASE_URL).toBe('https://api.example.com');
    });
  });

  describe('Environment flags', () => {
    it('should correctly set environment flags for development', async () => {
      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await loadEnvironment({
        VITE_ENV: 'development',
      });
      expect(ENVIRONMENT).toBe('development');
      expect(IS_DEVELOPMENT).toBe(true);
      expect(IS_PRODUCTION).toBe(false);
      expect(IS_STAGING).toBe(false);
    });

    it('should correctly set environment flags for production', async () => {
      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'https://api.example.com',
      });
      expect(ENVIRONMENT).toBe('production');
      expect(IS_DEVELOPMENT).toBe(false);
      expect(IS_PRODUCTION).toBe(true);
      expect(IS_STAGING).toBe(false);
    });

    it('should correctly set environment flags for staging', async () => {
      const { ENVIRONMENT, IS_DEVELOPMENT, IS_PRODUCTION, IS_STAGING } = await loadEnvironment({
        VITE_ENV: 'staging',
      });
      expect(ENVIRONMENT).toBe('staging');
      expect(IS_DEVELOPMENT).toBe(false);
      expect(IS_PRODUCTION).toBe(false);
      expect(IS_STAGING).toBe(true);
    });
  });

  describe('Debug mode', () => {
    it('should enable debug mode when VITE_DEBUG is true', async () => {
      const { DEBUG_MODE } = await loadEnvironment({ VITE_DEBUG: 'true' });
      expect(DEBUG_MODE).toBe(true);
    });

    it('should disable debug mode when VITE_DEBUG is false', async () => {
      const { DEBUG_MODE } = await loadEnvironment({ VITE_DEBUG: 'false' });
      expect(DEBUG_MODE).toBe(false);
    });

    it('should disable debug mode when VITE_DEBUG is not set', async () => {
      const { DEBUG_MODE } = await loadEnvironment();
      expect(DEBUG_MODE).toBe(false);
    });
  });

  describe('WebSocket configuration', () => {
    it('should auto-derive WebSocket URL from API URL in development', async () => {
      const { WS_URL } = await loadEnvironment({
        VITE_ENV: 'development',
        VITE_API_URL: 'http://localhost:8000',
      });
      expect(WS_URL).toBe('ws://localhost:8000');
    });

    it('should auto-derive WebSocket URL from HTTPS API URL in development', async () => {
      const { WS_URL } = await loadEnvironment({
        VITE_ENV: 'development',
        VITE_API_URL: 'https://localhost:8000',
      });
      expect(WS_URL).toBe('ws://localhost:8000');
    });

    it('should use explicit WebSocket URL when provided', async () => {
      const { WS_URL } = await loadEnvironment({
        VITE_ENV: 'development',
        VITE_API_URL: 'http://localhost:8000',
        VITE_WS_URL: 'ws://custom-ws:8001',
      });
      expect(WS_URL).toBe('ws://custom-ws:8001');
    });

    it('should not auto-derive WebSocket URL in production', async () => {
      const { WS_URL } = await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'https://api.example.com',
      });
      expect(WS_URL).toBe('');
    });

    it('should parse WebSocket numeric configuration correctly', async () => {
      const {
        WS_MAX_RECONNECT_ATTEMPTS,
        WS_RECONNECT_DELAY,
        WS_AI_BUFFER_TIMEOUT,
        WS_MAX_RECONNECT_DELAY,
        WS_HEARTBEAT_INTERVAL,
      } = await loadEnvironment();

      expect(WS_MAX_RECONNECT_ATTEMPTS).toBe(5);
      expect(WS_RECONNECT_DELAY).toBe(1000);
      expect(WS_AI_BUFFER_TIMEOUT).toBe(500);
      expect(WS_MAX_RECONNECT_DELAY).toBe(30000);
      expect(WS_HEARTBEAT_INTERVAL).toBe(30000);
    });
  });

  describe('Production validation', () => {
    it('should log error when VITE_API_URL is not configured in production', async () => {
      await loadEnvironment({ VITE_ENV: 'production' });
      expect(consoleErrorSpy).toHaveBeenCalledWith('CRITICAL: VITE_API_URL is not configured in production!');
      expect(consoleErrorSpy).toHaveBeenCalledWith('Please configure VITE_API_URL in CapRover environment variables');
    });

    it('should warn when API_BASE_URL contains localhost in production', async () => {
      await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'http://localhost:8000',
      });
      expect(consoleWarnSpy).toHaveBeenCalledWith('WARNING: API_BASE_URL contains localhost in production environment');
    });

    it('should not log warnings in production with proper configuration', async () => {
      await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'https://api.example.com',
      });
      expect(consoleErrorSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });
  });

  describe('Debug logging', () => {
    it('should log configuration in development mode', async () => {
      await loadEnvironment({
        VITE_ENV: 'development',
        VITE_API_URL: 'http://localhost:8000',
        VITE_DEBUG: 'false',
      });
      expect(consoleInfoSpy).toHaveBeenCalled();
      const calls = consoleInfoSpy.mock.calls.map(call => call[0]);
      expect(calls).toContain('🔧 DEBUG: Environment Configuration Analysis:');
    });

    it('should log configuration in debug mode regardless of environment', async () => {
      await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'https://api.example.com',
        VITE_DEBUG: 'true',
      });
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should not log configuration in production without debug mode', async () => {
      await loadEnvironment({
        VITE_ENV: 'production',
        VITE_API_URL: 'https://api.example.com',
        VITE_DEBUG: 'false',
      });
      // Only production validation messages, no debug messages
      const infoCallsWithDebug = consoleInfoSpy.mock.calls.filter(call =>
        call[0].includes('DEBUG') || call[0].includes('🔧')
      );
      expect(infoCallsWithDebug).toHaveLength(0);
    });
  });

  describe('config object', () => {
    it('should export a config object with all settings', async () => {
      const { config } = await loadEnvironment({
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
      });

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
