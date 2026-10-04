import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('../../config/environment', () => ({
  API_BASE_URL: 'http://test-api.com',
}));

const LOG_ENV_KEYS = [
  'VITE_LOG_ENABLED',
  'VITE_LOG_LEVEL',
  'VITE_LOG_SHOW_TIMESTAMP',
  'VITE_LOG_SHOW_LEVEL',
  'VITE_LOG_SHOW_FILE_PATH',
  'VITE_LOG_COLORIZE',
  'VITE_LOG_TO_CONSOLE',
  'VITE_LOG_TO_LOCALSTORAGE',
  'VITE_LOG_TO_REMOTE',
  'VITE_LOG_MAX_STORAGE_SIZE',
  'VITE_LOG_BATCH_SIZE',
  'VITE_LOG_BATCH_INTERVAL',
  'VITE_LOG_REMOTE_ENDPOINT',
];

// loggerConfig is evaluated when the module loads, so each case sets the environment and imports a fresh copy.
const loadConfig = async (env: Record<string, string> = {}) => {
  Object.entries(env).forEach(([key, value]) => vi.stubEnv(key, value));
  vi.resetModules();
  return import('../../config/logger.config');
};

describe('logger.config', () => {
  beforeEach(() => {
    LOG_ENV_KEYS.forEach(key => vi.stubEnv(key, undefined as unknown as string));
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe('defaults', () => {
    it('uses the documented defaults when no variable is set', async () => {
      const { loggerConfig } = await loadConfig();

      expect(loggerConfig).toEqual({
        enabled: true,
        level: 'info',
        showTimestamp: true,
        showLogLevel: true,
        showFilePath: false,
        colorize: true,
        outputs: { console: true, localStorage: false, remote: false },
        maxStorageSize: 5242880,
        batchSize: 10,
        batchInterval: 5000,
        remoteEndpoint: '',
      });
    });
  });

  describe('environment source', () => {
    it('reads import.meta.env in the browser', async () => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_LEVEL: 'debug' });

      expect(loggerConfig.level).toBe('debug');
    });

    it('reads process.env when there is no window', async () => {
      vi.stubGlobal('window', undefined);

      const { loggerConfig } = await loadConfig({ VITE_LOG_LEVEL: 'error' });

      expect(loggerConfig.level).toBe('error');
    });
  });

  describe('boolean variables', () => {
    it.each(['true', '1', 'yes', 'on', 'TRUE', 'Yes', 'ON'])('reads %s as true', async value => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_SHOW_FILE_PATH: value });

      expect(loggerConfig.showFilePath).toBe(true);
    });

    it.each(['false', '0', 'no', 'off', 'enabled', ''])('reads %j as false', async value => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_ENABLED: value });

      expect(loggerConfig.enabled).toBe(false);
    });

    it('maps each variable to its own setting', async () => {
      const { loggerConfig } = await loadConfig({
        VITE_LOG_SHOW_TIMESTAMP: 'false',
        VITE_LOG_SHOW_LEVEL: 'false',
        VITE_LOG_COLORIZE: 'false',
        VITE_LOG_TO_CONSOLE: 'false',
        VITE_LOG_TO_LOCALSTORAGE: 'true',
        VITE_LOG_TO_REMOTE: 'true',
      });

      expect(loggerConfig).toMatchObject({
        showTimestamp: false,
        showLogLevel: false,
        colorize: false,
        outputs: { console: false, localStorage: true, remote: true },
      });
    });
  });

  describe('log level', () => {
    it.each(['debug', 'info', 'warn', 'error', 'critical'])('accepts %s', async level => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_LEVEL: level });

      expect(loggerConfig.level).toBe(level);
    });

    it('is case insensitive', async () => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_LEVEL: 'WARN' });

      expect(loggerConfig.level).toBe('warn');
    });

    it.each(['verbose', ''])('falls back to info for %j', async level => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_LEVEL: level });

      expect(loggerConfig.level).toBe('info');
    });
  });

  describe('integer variables', () => {
    it('parses the three numeric settings', async () => {
      const { loggerConfig } = await loadConfig({
        VITE_LOG_MAX_STORAGE_SIZE: '1024',
        VITE_LOG_BATCH_SIZE: '25',
        VITE_LOG_BATCH_INTERVAL: '250',
      });

      expect(loggerConfig).toMatchObject({ maxStorageSize: 1024, batchSize: 25, batchInterval: 250 });
    });

    it.each(['abc', ''])('falls back to the default for %j', async value => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_BATCH_SIZE: value });

      expect(loggerConfig.batchSize).toBe(10);
    });

    it('keeps a negative value and a very large value as parsed', async () => {
      const { loggerConfig } = await loadConfig({
        VITE_LOG_BATCH_SIZE: '-5',
        VITE_LOG_MAX_STORAGE_SIZE: '9007199254740991',
      });

      expect(loggerConfig.batchSize).toBe(-5);
      expect(loggerConfig.maxStorageSize).toBe(9007199254740991);
    });
  });

  describe('remote endpoint', () => {
    it('uses the variable when it is set', async () => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_REMOTE_ENDPOINT: 'https://logs.example.com/in?x=1&y=2' });

      expect(loggerConfig.remoteEndpoint).toBe('https://logs.example.com/in?x=1&y=2');
    });

    it('has no endpoint for an empty variable (no backend serves the old default)', async () => {
      const { loggerConfig } = await loadConfig({ VITE_LOG_REMOTE_ENDPOINT: '' });

      expect(loggerConfig.remoteEndpoint).toBe('');
    });
  });

  describe('getLoggerConfig', () => {
    it('returns the loggerConfig object', async () => {
      const { loggerConfig, getLoggerConfig } = await loadConfig({ VITE_LOG_LEVEL: 'warn' });

      expect(getLoggerConfig()).toBe(loggerConfig);
    });
  });

  describe('debugLoggerConfig', () => {
    it('logs the mode, the config and every known variable inside one console group', async () => {
      const group = vi.spyOn(console, 'group').mockImplementation(() => {});
      const groupEnd = vi.spyOn(console, 'groupEnd').mockImplementation(() => {});
      const log = vi.spyOn(console, 'log').mockImplementation(() => {});
      const { loggerConfig, debugLoggerConfig } = await loadConfig({ VITE_LOG_LEVEL: 'debug' });

      debugLoggerConfig();

      expect(group).toHaveBeenCalledTimes(1);
      expect(groupEnd).toHaveBeenCalledTimes(1);
      expect(log).toHaveBeenCalledWith('Current config:', loggerConfig);
      expect(log).toHaveBeenCalledWith('  VITE_LOG_LEVEL=debug');
      expect(log).toHaveBeenCalledWith('  VITE_LOG_BATCH_SIZE=undefined');
      const variableLines = log.mock.calls.filter(([line]) => typeof line === 'string' && line.startsWith('  VITE_LOG_'));
      expect(variableLines).toHaveLength(LOG_ENV_KEYS.length);
    });
  });
});
