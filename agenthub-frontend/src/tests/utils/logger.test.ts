import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ComprehensiveLogger } from '../../utils/logger';
import { getLoggerConfig } from '../../config/logger.config';
import type { LoggerConfig } from '../../types/logger.types';

// Mock dependencies
vi.mock('../../config/logger.config', () => ({
  getLoggerConfig: vi.fn(() => ({
    enabled: true,
    level: 'debug',
    outputs: {
      console: true,
      localStorage: true,
      remote: false
    },
    showTimestamp: true,
    showLogLevel: true,
    showFilePath: true,
    colorize: true,
    batchSize: 50,
    batchInterval: 5000,
    maxStorageSize: 5242880
  }))
}));

// Mock fetch for remote logging tests
global.fetch = vi.fn();

describe('ComprehensiveLogger', () => {
  let logger: ComprehensiveLogger;
  let consoleDebugSpy: ReturnType<typeof vi.spyOn>;
  let consoleInfoSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let consoleGroupSpy: ReturnType<typeof vi.spyOn>;
  let consoleGroupCollapsedSpy: ReturnType<typeof vi.spyOn>;
  let consoleGroupEndSpy: ReturnType<typeof vi.spyOn>;
  let consoleTimeSpy: ReturnType<typeof vi.spyOn>;
  let consoleTimeEndSpy: ReturnType<typeof vi.spyOn>;
  let localStorageSetItemSpy: ReturnType<typeof vi.spyOn>;
  let localStorageGetItemSpy: ReturnType<typeof vi.spyOn>;
  let localStorageRemoveItemSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Set up console spies
    consoleDebugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    consoleGroupSpy = vi.spyOn(console, 'group').mockImplementation(() => {});
    consoleGroupCollapsedSpy = vi.spyOn(console, 'groupCollapsed').mockImplementation(() => {});
    consoleGroupEndSpy = vi.spyOn(console, 'groupEnd').mockImplementation(() => {});
    consoleTimeSpy = vi.spyOn(console, 'time').mockImplementation(() => {});
    consoleTimeEndSpy = vi.spyOn(console, 'timeEnd').mockImplementation(() => {});

    // Set up localStorage spies
    localStorageSetItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    localStorageGetItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => '[]');
    localStorageRemoveItemSpy = vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {});

    // Create new logger instance
    logger = new ComprehensiveLogger();
  });

  afterEach(() => {
    logger.destroy();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('initialization', () => {
    it('should initialize with default config', () => {
      const metadata = logger.getMetadata();
      expect(metadata.loggerId).toMatch(/^logger_\d+_[a-z0-9]+$/);
      expect(metadata.sessionId).toMatch(/^session_\d+_[a-z0-9]+$/);
      expect(metadata.config.enabled).toBe(true);
      expect(metadata.config.level).toBe('debug');
    });

    it('should accept custom config', () => {
      const customConfig: Partial<LoggerConfig> = {
        level: 'warn',
        outputs: {
          console: false,
          localStorage: false,
          remote: true
        }
      };
      
      const customLogger = new ComprehensiveLogger(customConfig);
      const metadata = customLogger.getMetadata();
      
      expect(metadata.config.level).toBe('warn');
      expect(metadata.config.outputs.console).toBe(false);
      expect(metadata.config.outputs.remote).toBe(true);
      
      customLogger.destroy();
    });

    it('should not initialize if disabled', () => {
      vi.mocked(getLoggerConfig).mockReturnValueOnce({
        enabled: false,
        level: 'debug',
        outputs: { console: true, localStorage: false, remote: false },
        showTimestamp: true,
        showLogLevel: true,
        showFilePath: true,
        colorize: true,
        batchSize: 50,
        batchInterval: 5000,
        maxStorageSize: 5242880
      });

      const disabledLogger = new ComprehensiveLogger();
      disabledLogger.info('Test message');
      
      expect(consoleInfoSpy).not.toHaveBeenCalled();
      
      disabledLogger.destroy();
    });
  });

  describe('log levels', () => {
    it('should log debug messages', () => {
      logger.debug('Debug message', { data: 'test' }, 'test.ts');
      
      expect(consoleDebugSpy).toHaveBeenCalled();
      const [message] = consoleDebugSpy.mock.calls[0];
      expect(message).toContain('DEBUG');
      expect(message).toContain('Debug message');
    });

    it('should log info messages', () => {
      logger.info('Info message', { data: 'test' });
      
      expect(consoleInfoSpy).toHaveBeenCalled();
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).toContain('INFO');
      expect(message).toContain('Info message');
    });

    it('should log warn messages', () => {
      logger.warn('Warning message', { data: 'test' });
      
      expect(consoleWarnSpy).toHaveBeenCalled();
      const [message] = consoleWarnSpy.mock.calls[0];
      expect(message).toContain('WARN');
      expect(message).toContain('Warning message');
    });

    it('should log error messages', () => {
      logger.error('Error message', { data: 'test' });
      
      expect(consoleErrorSpy).toHaveBeenCalled();
      const [message] = consoleErrorSpy.mock.calls[0];
      expect(message).toContain('ERROR');
      expect(message).toContain('Error message');
    });

    it('should log critical messages', () => {
      logger.critical('Critical message', { data: 'test' });
      
      expect(consoleErrorSpy).toHaveBeenCalled();
      const [message] = consoleErrorSpy.mock.calls[0];
      expect(message).toContain('CRITICAL');
      expect(message).toContain('Critical message');
    });

    it('should respect log level filtering', () => {
      logger.updateConfig({ level: 'warn' });
      
      logger.debug('Debug');
      logger.info('Info');
      logger.warn('Warning');
      logger.error('Error');
      
      expect(consoleDebugSpy).not.toHaveBeenCalled();
      expect(consoleInfoSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('conditional logging', () => {
    it('should log when condition is true', () => {
      logger.debugIf(true, 'Conditional debug', { value: 42 });
      logger.infoIf(true, 'Conditional info', { value: 42 });
      
      expect(consoleDebugSpy).toHaveBeenCalled();
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should not log when condition is false', () => {
      logger.debugIf(false, 'Should not appear');
      logger.infoIf(false, 'Should not appear');
      
      expect(consoleDebugSpy).not.toHaveBeenCalled();
      expect(consoleInfoSpy).not.toHaveBeenCalled();
    });
  });

  describe('formatting', () => {
    it('should format messages with timestamp', () => {
      logger.updateConfig({ showTimestamp: true });
      logger.info('Test message');
      
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).toMatch(/^\[[\d:]+\s*(AM|PM)?\]/);
    });

    it('should format messages without timestamp', () => {
      logger.updateConfig({ showTimestamp: false });
      logger.info('Test message');
      
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).not.toMatch(/^\[[\d:]+\s*(AM|PM)?\]/);
    });

    it('should include log level when enabled', () => {
      logger.updateConfig({ showLogLevel: true });
      logger.info('Test message');
      
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).toContain('[INFO]');
    });

    it('should exclude log level when disabled', () => {
      logger.updateConfig({ showLogLevel: false });
      logger.info('Test message');
      
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).not.toContain('[INFO]');
    });

    it('should include filepath when enabled and provided', () => {
      logger.updateConfig({ showFilePath: true });
      logger.info('Test message', undefined, 'component.ts');
      
      const [message] = consoleInfoSpy.mock.calls[0];
      expect(message).toContain('[component.ts]');
    });

    it('should apply color styling when enabled', () => {
      logger.updateConfig({ colorize: true });
      logger.info('Colored message');
      
      const [message, style] = consoleInfoSpy.mock.calls[0];
      expect(message).toContain('%c');
      expect(style).toContain('color:');
    });
  });

  describe('localStorage output', () => {
    it('should write logs to localStorage', () => {
      logger.updateConfig({ outputs: { console: true, localStorage: true, remote: false } });
      logger.info('Store this message');
      
      expect(localStorageSetItemSpy).toHaveBeenCalledWith('app_logs', expect.any(String));
      const stored = JSON.parse(localStorageSetItemSpy.mock.calls[0][1]);
      expect(stored).toHaveLength(1);
      expect(stored[0].message).toBe('Store this message');
    });

    it('should handle localStorage errors gracefully', () => {
      localStorageSetItemSpy.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });
      
      // Should not throw
      expect(() => {
        logger.info('This should not crash');
      }).not.toThrow();
      
      expect(consoleWarnSpy).toHaveBeenCalledWith('Failed to write to localStorage:', expect.any(Error));
    });

    it('should maintain size limit in localStorage', () => {
      const existingLogs = Array(1000).fill(null).map((_, i) => ({
        timestamp: new Date().toISOString(),
        level: 'info',
        message: `Old message ${i}`,
        loggerId: 'test',
        sessionId: 'test'
      }));
      
      localStorageGetItemSpy.mockReturnValue(JSON.stringify(existingLogs));
      logger.updateConfig({ maxStorageSize: 1000 }); // Very small limit
      
      logger.info('New message that exceeds limit');
      
      const [, stored] = localStorageSetItemSpy.mock.calls[0];
      expect(stored.length).toBeLessThan(1000);
    });
  });

  describe('remote logging', () => {
    it('should batch logs for remote endpoint', async () => {
      logger.updateConfig({
        outputs: { console: true, localStorage: false, remote: true },
        remoteEndpoint: 'https://api.example.com/logs',
        batchSize: 2,
        batchInterval: 1000
      });
      
      (global.fetch as any).mockResolvedValue({ ok: true });
      
      logger.info('Message 1');
      logger.info('Message 2');
      
      // Should trigger batch processing after 2 messages
      vi.advanceTimersByTime(1000);
      
      expect(global.fetch).toHaveBeenCalledWith('https://api.example.com/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.stringContaining('"logs"')
      });
    });

    it('should handle remote logging errors gracefully', async () => {
      logger.updateConfig({
        outputs: { console: true, localStorage: false, remote: true },
        remoteEndpoint: 'https://api.example.com/logs',
        batchSize: 1
      });
      
      (global.fetch as any).mockRejectedValue(new Error('Network error'));
      
      // Should not throw
      logger.info('Message despite network error');
      vi.advanceTimersByTime(5000);
      
      // Should still log to console
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should flush immediately for critical and error logs', () => {
      logger.updateConfig({
        outputs: { console: true, localStorage: false, remote: true },
        remoteEndpoint: 'https://api.example.com/logs'
      });
      
      (global.fetch as any).mockResolvedValue({ ok: true });
      
      logger.error('Error that should flush immediately');
      
      // Should not wait for batch interval
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('grouping', () => {
    it('should create log groups', () => {
      logger.group('Test Group');
      logger.info('Grouped message');
      logger.groupEnd();
      
      expect(consoleGroupSpy).toHaveBeenCalledWith('Test Group');
      expect(consoleInfoSpy).toHaveBeenCalled();
      expect(consoleGroupEndSpy).toHaveBeenCalled();
    });

    it('should create collapsed groups', () => {
      logger.group('Collapsed Group', true);
      logger.info('Hidden message');
      logger.groupEnd();
      
      expect(consoleGroupCollapsedSpy).toHaveBeenCalledWith('Collapsed Group');
      expect(consoleGroupEndSpy).toHaveBeenCalled();
    });

    it('should handle nested groups', () => {
      logger.group('Outer');
      logger.group('Inner');
      logger.info('Nested message');
      logger.groupEnd();
      logger.groupEnd();
      
      expect(consoleGroupSpy).toHaveBeenCalledTimes(2);
      expect(consoleGroupEndSpy).toHaveBeenCalledTimes(2);
    });

    it('should not group when log level is too high', () => {
      logger.updateConfig({ level: 'error' });
      
      logger.group('Should not appear');
      logger.groupEnd();
      
      expect(consoleGroupSpy).not.toHaveBeenCalled();
      expect(consoleGroupEndSpy).not.toHaveBeenCalled();
    });
  });

  describe('timing', () => {
    it('should measure time between calls', () => {
      logger.time('operation');
      
      // Simulate some time passing
      vi.advanceTimersByTime(123);
      
      logger.timeEnd('operation');
      
      expect(consoleTimeSpy).toHaveBeenCalledWith('operation');
      expect(consoleTimeEndSpy).toHaveBeenCalledWith('operation');
      expect(consoleDebugSpy).toHaveBeenCalledWith(
        expect.stringContaining('Timer operation:'),
        expect.any(String),
        ''
      );
    });

    it('should handle non-existent timers', () => {
      logger.timeEnd('non-existent');
      
      // Should not crash
      expect(consoleTimeEndSpy).toHaveBeenCalled();
    });

    it('should not time when log level is too high', () => {
      logger.updateConfig({ level: 'error' });
      
      logger.time('operation');
      logger.timeEnd('operation');
      
      expect(consoleTimeSpy).not.toHaveBeenCalled();
      expect(consoleTimeEndSpy).not.toHaveBeenCalled();
    });
  });

  describe('stored logs', () => {
    it('should retrieve stored logs', () => {
      const mockLogs = [
        { timestamp: '2025-01-10T10:00:00Z', level: 'info', message: 'Test 1' },
        { timestamp: '2025-01-10T10:01:00Z', level: 'warn', message: 'Test 2' }
      ];
      localStorageGetItemSpy.mockReturnValue(JSON.stringify(mockLogs));
      
      const logs = logger.getStoredLogs();
      expect(logs).toHaveLength(2);
      expect(logs[0].message).toBe('Test 1');
    });

    it('should return empty array when no logs exist', () => {
      localStorageGetItemSpy.mockReturnValue(null);
      
      const logs = logger.getStoredLogs();
      expect(logs).toEqual([]);
    });

    it('should handle corrupted stored logs', () => {
      localStorageGetItemSpy.mockReturnValue('invalid json');
      
      const logs = logger.getStoredLogs();
      expect(logs).toEqual([]);
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it('should clear stored logs', () => {
      logger.clearStoredLogs();
      
      expect(localStorageRemoveItemSpy).toHaveBeenCalledWith('app_logs');
    });

    it('should handle errors when clearing logs', () => {
      localStorageRemoveItemSpy.mockImplementation(() => {
        throw new Error('Permission denied');
      });
      
      // Should not throw
      expect(() => logger.clearStoredLogs()).not.toThrow();
      expect(consoleWarnSpy).toHaveBeenCalled();
    });
  });

  describe('log download', () => {
    it('should download logs as JSON file', () => {
      const mockLogs = [{ timestamp: '2025-01-10T10:00:00Z', level: 'info', message: 'Download me' }];
      localStorageGetItemSpy.mockReturnValue(JSON.stringify(mockLogs));
      
      const createElementSpy = vi.spyOn(document, 'createElement');
      const clickSpy = vi.fn();
      const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL');
      
      createElementSpy.mockReturnValue({
        href: '',
        download: '',
        click: clickSpy,
        style: {}
      } as any);
      
      logger.downloadLogs();
      
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(clickSpy).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });

    it('should handle download errors', () => {
      localStorageGetItemSpy.mockImplementation(() => {
        throw new Error('Failed to get logs');
      });
      
      logger.downloadLogs();
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to download logs'),
        expect.any(String),
        expect.any(Error)
      );
    });
  });

  describe('configuration updates', () => {
    it('should update configuration dynamically', () => {
      logger.updateConfig({ level: 'warn', colorize: false });
      
      const metadata = logger.getMetadata();
      expect(metadata.config.level).toBe('warn');
      expect(metadata.config.colorize).toBe(false);
      
      // Test that new config is applied
      logger.debug('Should not appear');
      logger.warn('Should appear');
      
      expect(consoleDebugSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it('should restart batch processing when config changes', () => {
      logger.updateConfig({
        outputs: { console: true, localStorage: false, remote: true },
        batchInterval: 2000
      });
      
      // Should have new timer with new interval
      const metadata = logger.getMetadata();
      expect(metadata.config.batchInterval).toBe(2000);
    });
  });

  describe('lifecycle', () => {
    it('should flush logs on page unload', () => {
      const flushSpy = vi.spyOn(logger, 'flush');
      
      // Trigger beforeunload event
      window.dispatchEvent(new Event('beforeunload'));
      
      expect(flushSpy).toHaveBeenCalled();
    });

    it('should flush logs when tab becomes hidden', () => {
      const flushSpy = vi.spyOn(logger, 'flush');
      
      // Mock document.hidden
      Object.defineProperty(document, 'hidden', {
        value: true,
        writable: true
      });
      
      // Trigger visibilitychange event
      document.dispatchEvent(new Event('visibilitychange'));
      
      expect(flushSpy).toHaveBeenCalled();
    });

    it('should clean up resources on destroy', () => {
      logger.updateConfig({
        outputs: { console: true, localStorage: false, remote: true }
      });
      
      const metadata = logger.getMetadata();
      expect(metadata.queueSize).toBe(0);
      
      logger.info('Message 1');
      logger.info('Message 2');
      
      expect(logger.getMetadata().queueSize).toBeGreaterThan(0);
      
      logger.destroy();
      
      expect(logger.getMetadata().queueSize).toBe(0);
    });
  });

  describe('edge cases', () => {
    it('should handle circular references in data', () => {
      const circular: any = { a: 1 };
      circular.self = circular;
      
      // Should not throw
      expect(() => {
        logger.info('Circular reference', circular);
      }).not.toThrow();
    });

    it('should handle very large messages', () => {
      const largeMessage = 'x'.repeat(10000);
      const largeData = { data: 'y'.repeat(10000) };
      
      // Should not throw
      expect(() => {
        logger.info(largeMessage, largeData);
      }).not.toThrow();
      
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should handle undefined and null data', () => {
      logger.info('Message with undefined', undefined);
      logger.info('Message with null', null);
      
      expect(consoleInfoSpy).toHaveBeenCalledTimes(2);
    });
  });
});