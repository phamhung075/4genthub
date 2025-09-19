/**
 * Comprehensive unit tests for the logger system
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { ComprehensiveLogger } from './logger';
import { LogLevel, LoggerConfig } from '../types/logger.types';

// Mock console methods
const mockConsole = {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  log: vi.fn(),
  group: vi.fn(),
  groupCollapsed: vi.fn(),
  groupEnd: vi.fn(),
  time: vi.fn(),
  timeEnd: vi.fn()
};

// Mock fetch for remote logging
global.fetch = vi.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

// Mock performance.now
Object.defineProperty(window, 'performance', {
  value: {
    now: vi.fn(() => 1000)
  }
});

describe('ComprehensiveLogger', () => {
  let logger: ComprehensiveLogger;
  let originalConsole: Console;

  beforeEach(() => {
    // Save original console
    originalConsole = global.console;

    // Replace console with mocks
    global.console = mockConsole as unknown as Console;

    // Clear all mocks
    vi.clearAllMocks();

    // Create logger with test configuration
    const testConfig: Partial<LoggerConfig> = {
      enabled: true,
      level: 'debug',
      showTimestamp: false,
      showLogLevel: true,
      showFilePath: false,
      colorize: false,
      outputs: ['console'],
      localStorageMaxSize: 100,
      batchSize: 5,
      batchInterval: 1000
    };

    logger = new ComprehensiveLogger(testConfig);
  });

  afterEach(() => {
    // Restore original console
    global.console = originalConsole;

    // Cleanup logger
    logger.destroy();
  });

  describe('Basic Logging', () => {
    test('should log debug messages', () => {
      logger.debug('Test debug message');
      expect(mockConsole.debug).toHaveBeenCalledWith('[DEBUG] Test debug message', '');
    });

    test('should log info messages', () => {
      logger.info('Test info message');
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] Test info message', '');
    });

    test('should log warn messages', () => {
      logger.warn('Test warn message');
      expect(mockConsole.warn).toHaveBeenCalledWith('[WARN] Test warn message', '');
    });

    test('should log error messages', () => {
      logger.error('Test error message');
      expect(mockConsole.error).toHaveBeenCalledWith('[ERROR] Test error message', '');
    });

    test('should log critical messages', () => {
      logger.critical('Test critical message');
      expect(mockConsole.error).toHaveBeenCalledWith('[CRITICAL] Test critical message', '');
    });

    test('should include data in logs', () => {
      const testData = { userId: 123, action: 'login' };
      logger.info('User action', testData);
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] User action', testData);
    });
  });

  describe('Log Level Filtering', () => {
    test('should respect minimum log level', () => {
      // Create logger with warn level
      const warnLogger = new ComprehensiveLogger({
        level: 'warn',
        outputs: ['console']
      });

      warnLogger.debug('Should not appear');
      warnLogger.info('Should not appear');
      warnLogger.warn('Should appear');
      warnLogger.error('Should appear');

      expect(mockConsole.debug).not.toHaveBeenCalled();
      expect(mockConsole.info).not.toHaveBeenCalled();
      expect(mockConsole.warn).toHaveBeenCalled();
      expect(mockConsole.error).toHaveBeenCalled();

      warnLogger.destroy();
    });

    test('should not log when disabled', () => {
      const disabledLogger = new ComprehensiveLogger({
        enabled: false,
        outputs: ['console']
      });

      disabledLogger.error('Should not appear');
      expect(mockConsole.error).not.toHaveBeenCalled();

      disabledLogger.destroy();
    });
  });

  describe('Conditional Logging', () => {
    test('should log when condition is true', () => {
      logger.debugIf(true, 'Conditional debug');
      expect(mockConsole.debug).toHaveBeenCalledWith('[DEBUG] Conditional debug', '');
    });

    test('should not log when condition is false', () => {
      logger.debugIf(false, 'Should not appear');
      expect(mockConsole.debug).not.toHaveBeenCalled();
    });

    test('should support conditional info logging', () => {
      logger.infoIf(true, 'Conditional info');
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] Conditional info', '');
    });
  });

  describe('Grouping', () => {
    test('should create log groups', () => {
      logger.group('Test Group');
      expect(mockConsole.group).toHaveBeenCalledWith('Test Group');
    });

    test('should create collapsed log groups', () => {
      logger.group('Collapsed Group', true);
      expect(mockConsole.groupCollapsed).toHaveBeenCalledWith('Collapsed Group');
    });

    test('should end log groups', () => {
      logger.groupEnd();
      expect(mockConsole.groupEnd).toHaveBeenCalled();
    });
  });

  describe('Timing', () => {
    test('should start and end timers', () => {
      logger.time('test-timer');
      expect(mockConsole.time).toHaveBeenCalledWith('test-timer');

      logger.timeEnd('test-timer');
      expect(mockConsole.timeEnd).toHaveBeenCalledWith('test-timer');
      expect(mockConsole.debug).toHaveBeenCalledWith('[DEBUG] Timer test-timer: 0.00ms', '');
    });
  });

  describe('LocalStorage Integration', () => {
    test('should save logs to localStorage', () => {
      const localStorageLogger = new ComprehensiveLogger({
        outputs: ['localStorage'],
        enabled: true
      });

      mockLocalStorage.getItem.mockReturnValue(null);

      localStorageLogger.info('Test localStorage');

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'app_logs',
        expect.stringContaining('Test localStorage')
      );

      localStorageLogger.destroy();
    });

    test('should retrieve stored logs', () => {
      const mockLogs = JSON.stringify([
        { message: 'Test log', level: 'info', timestamp: '2023-01-01T00:00:00.000Z' }
      ]);

      mockLocalStorage.getItem.mockReturnValue(mockLogs);

      const storedLogs = logger.getStoredLogs();
      expect(storedLogs).toHaveLength(1);
      expect(storedLogs[0].message).toBe('Test log');
    });

    test('should clear stored logs', () => {
      logger.clearStoredLogs();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('app_logs');
    });
  });

  describe('Remote Logging', () => {
    test('should send logs to remote endpoint', async () => {
      const mockFetch = global.fetch as any;
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      } as Response);

      const remoteLogger = new ComprehensiveLogger({
        outputs: ['remote'],
        remoteEndpoint: 'http://localhost:8000/api/logs',
        batchSize: 1,
        enabled: true
      });

      remoteLogger.error('Test remote logging');

      // Wait for flush to complete
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/logs',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('Test remote logging')
        })
      );

      remoteLogger.destroy();
    });

    test('should handle remote logging failures gracefully', async () => {
      const mockFetch = global.fetch as any;
      mockFetch.mockRejectedValue(new Error('Network error'));

      const remoteLogger = new ComprehensiveLogger({
        outputs: ['remote'],
        remoteEndpoint: 'http://localhost:8000/api/logs',
        batchSize: 1,
        enabled: true
      });

      // Should not throw
      remoteLogger.error('Test failed remote');

      // Wait for flush to complete
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalled();

      remoteLogger.destroy();
    });
  });

  describe('Configuration', () => {
    test('should update configuration', () => {
      const newConfig = {
        level: 'error' as LogLevel,
        colorize: true
      };

      logger.updateConfig(newConfig);

      // Test that debug is now filtered out
      logger.debug('Should not appear');
      expect(mockConsole.debug).not.toHaveBeenCalled();

      // Test that error still works
      logger.error('Should appear');
      expect(mockConsole.error).toHaveBeenCalled();
    });

    test('should return metadata', () => {
      const metadata = logger.getMetadata();

      expect(metadata).toHaveProperty('loggerId');
      expect(metadata).toHaveProperty('sessionId');
      expect(metadata).toHaveProperty('queueSize');
      expect(metadata).toHaveProperty('config');
      expect(typeof metadata.loggerId).toBe('string');
      expect(typeof metadata.sessionId).toBe('string');
      expect(typeof metadata.queueSize).toBe('number');
    });
  });

  describe('Message Formatting', () => {
    test('should format messages with timestamp', () => {
      const timestampLogger = new ComprehensiveLogger({
        showTimestamp: true,
        showLogLevel: false,
        outputs: ['console']
      });

      timestampLogger.info('Test message');

      const calls = mockConsole.info.mock.calls;
      expect(calls[0][0]).toMatch(/^\[\d{1,2}:\d{2}:\d{2}\s[AP]M\] Test message$/);

      timestampLogger.destroy();
    });

    test('should format messages with filepath', () => {
      const filepathLogger = new ComprehensiveLogger({
        showFilePath: true,
        showTimestamp: false,
        showLogLevel: false,
        outputs: ['console']
      });

      filepathLogger.info('Test message', undefined, 'test.ts');

      expect(mockConsole.info).toHaveBeenCalledWith('[test.ts] Test message', '');

      filepathLogger.destroy();
    });
  });

  describe('Performance and Edge Cases', () => {
    test('should handle undefined data gracefully', () => {
      logger.info('Test message', undefined);
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] Test message', '');
    });

    test('should handle null data gracefully', () => {
      logger.info('Test message', null);
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] Test message', null);
    });

    test('should handle complex data objects', () => {
      const complexData = {
        nested: { value: 123 },
        array: [1, 2, 3],
        date: new Date(),
        func: () => 'test'
      };

      logger.info('Complex data', complexData);
      expect(mockConsole.info).toHaveBeenCalledWith('[INFO] Complex data', complexData);
    });

    test('should handle localStorage quota exceeded', () => {
      const quotaLogger = new ComprehensiveLogger({
        outputs: ['localStorage'],
        enabled: true
      });

      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      // Should not throw
      quotaLogger.info('Test quota exceeded');

      quotaLogger.destroy();
    });
  });

  describe('Cleanup and Destruction', () => {
    test('should cleanup resources on destroy', () => {
      const destroyLogger = new ComprehensiveLogger({
        outputs: ['remote'],
        batchInterval: 100
      });

      const metadata = destroyLogger.getMetadata();
      expect(metadata.queueSize).toBe(0);

      destroyLogger.destroy();

      // Add logs after destroy - should still work but without timers
      destroyLogger.info('After destroy');
    });
  });
});