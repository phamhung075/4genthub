import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  loggerConfig,
  getLoggerConfig,
  environmentPresets,
  debugLoggerConfig,
  baseConfig,
  developmentConfig,
  stagingConfig,
  productionConfig,
  testConfig,
} from '../../config/logger.config';

// Mock import.meta.env
vi.mock('../../config/environment', () => ({
  API_BASE_URL: 'http://test-api.com',
}));

describe('logger.config', () => {
  // Store original values
  const originalImportMeta = (global as any).import?.meta;
  const originalProcess = (global as any).process;
  const originalWindow = (global as any).window;
  
  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
    
    // Reset global objects
    (global as any).import = { meta: { env: {} } };
    (global as any).process = { env: {} };
    (global as any).window = {};
  });

  afterEach(() => {
    // Restore original values
    if (originalImportMeta !== undefined) {
      (global as any).import = { meta: originalImportMeta };
    }
    if (originalProcess !== undefined) {
      (global as any).process = originalProcess;
    }
    if (originalWindow !== undefined) {
      (global as any).window = originalWindow;
    }
    
    // Clear module cache to ensure fresh imports
    vi.resetModules();
  });

  describe('getEnvVar', () => {
    it('should read from import.meta.env when available', async () => {
      (global as any).import.meta.env.VITE_LOG_LEVEL = 'debug';
      
      // Re-import to get fresh module with mocked env
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.level).toBe('debug');
    });

    it('should fall back to process.env when import.meta.env is not available', async () => {
      delete (global as any).import;
      (global as any).process.env.VITE_LOG_LEVEL = 'warn';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.level).toBe('warn');
    });

    it('should fall back to window._env_ when other sources are not available', async () => {
      delete (global as any).import;
      delete (global as any).process;
      (global as any).window._env_ = { VITE_LOG_LEVEL: 'error' };
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.level).toBe('error');
    });

    it('should return undefined when no environment is available', async () => {
      delete (global as any).import;
      delete (global as any).process;
      delete (global as any).window;
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      // Should use default value when env var is undefined
      expect(freshConfig.level).toBe('info'); // default log level
    });
  });

  describe('getEnvBoolean', () => {
    const testBooleanValues = async (envKey: string, configKey: keyof typeof loggerConfig) => {
      // Test true values
      for (const trueValue of ['true', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']) {
        (global as any).import.meta.env[envKey] = trueValue;
        const { loggerConfig: freshConfig } = await import('../../config/logger.config');
        expect(freshConfig[configKey]).toBe(true);
        vi.resetModules();
      }

      // Test false values
      for (const falseValue of ['false', 'FALSE', '0', 'no', 'NO', 'off', 'OFF']) {
        (global as any).import.meta.env[envKey] = falseValue;
        const { loggerConfig: freshConfig } = await import('../../config/logger.config');
        expect(freshConfig[configKey]).toBe(false);
        vi.resetModules();
      }
    };

    it('should parse boolean values correctly for enabled', async () => {
      await testBooleanValues('VITE_LOG_ENABLED', 'enabled');
    });

    it('should parse boolean values correctly for showTimestamp', async () => {
      await testBooleanValues('VITE_LOG_SHOW_TIMESTAMP', 'showTimestamp');
    });

    it('should parse boolean values correctly for colorize', async () => {
      await testBooleanValues('VITE_LOG_COLORIZE', 'colorize');
    });

    it('should return default value when env var is undefined', async () => {
      // All defaults should be true except some output options
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.enabled).toBe(true);
      expect(freshConfig.showTimestamp).toBe(true);
      expect(freshConfig.outputs.console).toBe(true);
      expect(freshConfig.outputs.localStorage).toBe(false);
      expect(freshConfig.outputs.remote).toBe(false);
    });
  });

  describe('getEnvLogLevel', () => {
    const validLevels = ['debug', 'info', 'warn', 'error', 'critical'];

    it('should parse valid log levels correctly', async () => {
      for (const level of validLevels) {
        (global as any).import.meta.env.VITE_LOG_LEVEL = level;
        const { loggerConfig: freshConfig } = await import('../../config/logger.config');
        expect(freshConfig.level).toBe(level);
        vi.resetModules();
      }
    });

    it('should parse log levels case-insensitively', async () => {
      for (const level of ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']) {
        (global as any).import.meta.env.VITE_LOG_LEVEL = level;
        const { loggerConfig: freshConfig } = await import('../../config/logger.config');
        expect(freshConfig.level).toBe(level.toLowerCase());
        vi.resetModules();
      }
    });

    it('should default to "info" for invalid log levels', async () => {
      (global as any).import.meta.env.VITE_LOG_LEVEL = 'invalid-level';
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.level).toBe('info');
    });

    it('should default to "info" when env var is undefined', async () => {
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.level).toBe('info');
    });
  });

  describe('getEnvInteger', () => {
    it('should parse valid integers correctly', async () => {
      (global as any).import.meta.env.VITE_LOG_BATCH_SIZE = '25';
      (global as any).import.meta.env.VITE_LOG_BATCH_INTERVAL = '10000';
      (global as any).import.meta.env.VITE_LOG_MAX_STORAGE_SIZE = '1048576';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.batchSize).toBe(25);
      expect(freshConfig.batchInterval).toBe(10000);
      expect(freshConfig.maxStorageSize).toBe(1048576);
    });

    it('should return default value for invalid integers', async () => {
      (global as any).import.meta.env.VITE_LOG_BATCH_SIZE = 'not-a-number';
      (global as any).import.meta.env.VITE_LOG_BATCH_INTERVAL = 'abc';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.batchSize).toBe(10); // default
      expect(freshConfig.batchInterval).toBe(5000); // default
    });

    it('should return default value when env var is undefined', async () => {
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.maxStorageSize).toBe(5242880); // 5MB default
      expect(freshConfig.batchSize).toBe(10);
      expect(freshConfig.batchInterval).toBe(5000);
    });

    it('should handle NaN correctly', async () => {
      (global as any).import.meta.env.VITE_LOG_BATCH_SIZE = 'NaN';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.batchSize).toBe(10); // default
    });
  });

  describe('loggerConfig export', () => {
    it('should have all required properties', () => {
      expect(loggerConfig).toHaveProperty('enabled');
      expect(loggerConfig).toHaveProperty('level');
      expect(loggerConfig).toHaveProperty('showTimestamp');
      expect(loggerConfig).toHaveProperty('showLogLevel');
      expect(loggerConfig).toHaveProperty('showFilePath');
      expect(loggerConfig).toHaveProperty('colorize');
      expect(loggerConfig).toHaveProperty('outputs');
      expect(loggerConfig).toHaveProperty('maxStorageSize');
      expect(loggerConfig).toHaveProperty('batchSize');
      expect(loggerConfig).toHaveProperty('batchInterval');
      expect(loggerConfig).toHaveProperty('remoteEndpoint');
    });

    it('should have correct output properties', () => {
      expect(loggerConfig.outputs).toHaveProperty('console');
      expect(loggerConfig.outputs).toHaveProperty('localStorage');
      expect(loggerConfig.outputs).toHaveProperty('remote');
    });

    it('should use correct default values', async () => {
      // Clear all env vars to test defaults
      (global as any).import.meta.env = {};
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.enabled).toBe(true);
      expect(freshConfig.level).toBe('info');
      expect(freshConfig.showTimestamp).toBe(true);
      expect(freshConfig.showLogLevel).toBe(true);
      expect(freshConfig.showFilePath).toBe(false);
      expect(freshConfig.colorize).toBe(true);
      expect(freshConfig.outputs.console).toBe(true);
      expect(freshConfig.outputs.localStorage).toBe(false);
      expect(freshConfig.outputs.remote).toBe(false);
      expect(freshConfig.maxStorageSize).toBe(5242880);
      expect(freshConfig.batchSize).toBe(10);
      expect(freshConfig.batchInterval).toBe(5000);
      expect(freshConfig.remoteEndpoint).toBe('http://test-api.com/api/logs/frontend');
    });

    it('should override defaults with env vars', async () => {
      (global as any).import.meta.env = {
        VITE_LOG_ENABLED: 'false',
        VITE_LOG_LEVEL: 'debug',
        VITE_LOG_SHOW_TIMESTAMP: 'false',
        VITE_LOG_SHOW_LEVEL: 'false',
        VITE_LOG_SHOW_FILE_PATH: 'true',
        VITE_LOG_COLORIZE: 'false',
        VITE_LOG_TO_CONSOLE: 'false',
        VITE_LOG_TO_LOCALSTORAGE: 'true',
        VITE_LOG_TO_REMOTE: 'true',
        VITE_LOG_MAX_STORAGE_SIZE: '1048576',
        VITE_LOG_BATCH_SIZE: '20',
        VITE_LOG_BATCH_INTERVAL: '10000',
        VITE_LOG_REMOTE_ENDPOINT: 'http://custom-log-endpoint.com',
      };
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.enabled).toBe(false);
      expect(freshConfig.level).toBe('debug');
      expect(freshConfig.showTimestamp).toBe(false);
      expect(freshConfig.showLogLevel).toBe(false);
      expect(freshConfig.showFilePath).toBe(true);
      expect(freshConfig.colorize).toBe(false);
      expect(freshConfig.outputs.console).toBe(false);
      expect(freshConfig.outputs.localStorage).toBe(true);
      expect(freshConfig.outputs.remote).toBe(true);
      expect(freshConfig.maxStorageSize).toBe(1048576);
      expect(freshConfig.batchSize).toBe(20);
      expect(freshConfig.batchInterval).toBe(10000);
      expect(freshConfig.remoteEndpoint).toBe('http://custom-log-endpoint.com');
    });
  });

  describe('getLoggerConfig', () => {
    it('should return the same config as loggerConfig export', () => {
      expect(getLoggerConfig()).toEqual(loggerConfig);
    });

    it('should return config based on current env vars', async () => {
      (global as any).import.meta.env.VITE_LOG_LEVEL = 'critical';
      
      const { getLoggerConfig: freshGetter } = await import('../../config/logger.config');
      const config = freshGetter();
      expect(config.level).toBe('critical');
    });
  });

  describe('environmentPresets', () => {
    it('should have presets for all environments', () => {
      expect(environmentPresets).toHaveProperty('development');
      expect(environmentPresets).toHaveProperty('staging');
      expect(environmentPresets).toHaveProperty('production');
      expect(environmentPresets).toHaveProperty('test');
    });

    it('should have correct development preset', () => {
      const devPreset = environmentPresets.development;
      expect(devPreset.VITE_LOG_ENABLED).toBe('true');
      expect(devPreset.VITE_LOG_LEVEL).toBe('debug');
      expect(devPreset.VITE_LOG_SHOW_FILE_PATH).toBe('true');
      expect(devPreset.VITE_LOG_TO_REMOTE).toBe('false');
    });

    it('should have correct production preset', () => {
      const prodPreset = environmentPresets.production;
      expect(prodPreset.VITE_LOG_ENABLED).toBe('true');
      expect(prodPreset.VITE_LOG_LEVEL).toBe('warn');
      expect(prodPreset.VITE_LOG_TO_CONSOLE).toBe('false');
      expect(prodPreset.VITE_LOG_TO_REMOTE).toBe('true');
      expect(prodPreset.VITE_LOG_MAX_STORAGE_SIZE).toBe('2097152');
    });

    it('should have correct test preset', () => {
      const testPreset = environmentPresets.test;
      expect(testPreset.VITE_LOG_ENABLED).toBe('false');
      expect(testPreset.VITE_LOG_LEVEL).toBe('error');
      expect(testPreset.VITE_LOG_TO_CONSOLE).toBe('true');
      expect(testPreset.VITE_LOG_TO_REMOTE).toBe('false');
    });
  });

  describe('debugLoggerConfig', () => {
    let consoleMocks: any;

    beforeEach(() => {
      consoleMocks = {
        group: vi.spyOn(console, 'group').mockImplementation(),
        log: vi.spyOn(console, 'log').mockImplementation(),
        groupEnd: vi.spyOn(console, 'groupEnd').mockImplementation(),
      };
    });

    afterEach(() => {
      Object.values(consoleMocks).forEach((mock: any) => mock.mockRestore());
    });

    it('should log configuration information', () => {
      debugLoggerConfig();
      
      expect(consoleMocks.group).toHaveBeenCalledWith('🔧 Logger Configuration Debug');
      expect(consoleMocks.log).toHaveBeenCalledWith('Environment Mode:', expect.anything());
      expect(consoleMocks.log).toHaveBeenCalledWith('Is Development:', expect.anything());
      expect(consoleMocks.log).toHaveBeenCalledWith('Current config:', expect.any(Object));
      expect(consoleMocks.log).toHaveBeenCalledWith('Environment variables:');
      expect(consoleMocks.groupEnd).toHaveBeenCalled();
    });

    it('should log all known environment variable keys', () => {
      (global as any).import.meta.env = {
        MODE: 'test',
        DEV: false,
        VITE_LOG_ENABLED: 'true',
        VITE_LOG_LEVEL: 'debug',
      };
      
      debugLoggerConfig();
      
      // Check that it logs each known env var
      expect(consoleMocks.log).toHaveBeenCalledWith(expect.stringContaining('VITE_LOG_ENABLED=true'));
      expect(consoleMocks.log).toHaveBeenCalledWith(expect.stringContaining('VITE_LOG_LEVEL=debug'));
      expect(consoleMocks.log).toHaveBeenCalledWith(expect.stringContaining('VITE_LOG_SHOW_TIMESTAMP=undefined'));
    });

    it('should handle missing import.meta gracefully', () => {
      delete (global as any).import;
      
      expect(() => debugLoggerConfig()).not.toThrow();
      expect(consoleMocks.group).toHaveBeenCalled();
      expect(consoleMocks.groupEnd).toHaveBeenCalled();
    });
  });

  describe('legacy exports', () => {
    it('should export baseConfig as alias for loggerConfig', () => {
      expect(baseConfig).toBe(loggerConfig);
    });

    it('should export developmentConfig as alias for loggerConfig', () => {
      expect(developmentConfig).toBe(loggerConfig);
    });

    it('should export stagingConfig as alias for loggerConfig', () => {
      expect(stagingConfig).toBe(loggerConfig);
    });

    it('should export productionConfig as alias for loggerConfig', () => {
      expect(productionConfig).toBe(loggerConfig);
    });

    it('should export testConfig as alias for loggerConfig', () => {
      expect(testConfig).toBe(loggerConfig);
    });
  });

  describe('edge cases', () => {
    it('should handle empty string env vars', async () => {
      (global as any).import.meta.env.VITE_LOG_LEVEL = '';
      (global as any).import.meta.env.VITE_LOG_BATCH_SIZE = '';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      // Empty string should not match valid log levels, so defaults to 'info'
      expect(freshConfig.level).toBe('info');
      // Empty string parseInt returns NaN, so defaults to 10
      expect(freshConfig.batchSize).toBe(10);
    });

    it('should handle whitespace in boolean env vars', async () => {
      (global as any).import.meta.env.VITE_LOG_ENABLED = ' true ';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      // toLowerCase() is called but trim() is not, so this won't match
      expect(freshConfig.enabled).toBe(false);
    });

    it('should handle special characters in remote endpoint', async () => {
      const specialEndpoint = 'https://log-api.example.com/logs?source=frontend&version=1.0';
      (global as any).import.meta.env.VITE_LOG_REMOTE_ENDPOINT = specialEndpoint;
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.remoteEndpoint).toBe(specialEndpoint);
    });

    it('should handle very large integer values', async () => {
      (global as any).import.meta.env.VITE_LOG_MAX_STORAGE_SIZE = '999999999999';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.maxStorageSize).toBe(999999999999);
    });

    it('should handle negative integer values', async () => {
      (global as any).import.meta.env.VITE_LOG_BATCH_SIZE = '-5';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.batchSize).toBe(-5); // parseInt accepts negative values
    });

    it('should handle mixed case boolean values', async () => {
      (global as any).import.meta.env.VITE_LOG_ENABLED = 'TrUe';
      (global as any).import.meta.env.VITE_LOG_COLORIZE = 'YeS';
      (global as any).import.meta.env.VITE_LOG_TO_CONSOLE = 'On';
      
      const { loggerConfig: freshConfig } = await import('../../config/logger.config');
      expect(freshConfig.enabled).toBe(true);
      expect(freshConfig.colorize).toBe(true);
      expect(freshConfig.outputs.console).toBe(true);
    });
  });
});