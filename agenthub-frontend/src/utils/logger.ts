/**
 * Comprehensive Frontend Logger System
 *
 * Features:
 * - Multiple log levels (debug, info, warn, error, critical)
 * - Configurable output targets (console, localStorage, remote)
 * - Performance optimized with conditional logging
 * - TypeScript support with proper typing
 * - Group/ungroup support for related logs
 * - Timer functions for performance measurement
 * - Environment-based configuration
 * - Lazy evaluation and buffering
 */

import {
  LogLevel,
  LogEntry,
  LoggerConfig,
  LoggerMetadata,
  TimerEntry,
  LoggerGroup,
  LOG_LEVELS,
  LOG_COLORS
} from '../types/logger.types';
import { getLoggerConfig } from '../config/logger.config';

class ComprehensiveLogger {
  private config: LoggerConfig;
  private logQueue: LogEntry[] = [];
  private loggerId: string;
  private sessionId: string;
  private timers: Map<string, TimerEntry> = new Map();
  private groupStack: LoggerGroup[] = [];
  private batchTimer: NodeJS.Timeout | null = null;

  constructor(customConfig?: Partial<LoggerConfig>) {
    // Load configuration
    this.config = { ...getLoggerConfig(), ...customConfig };

    // Generate unique identifiers
    this.loggerId = `logger_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    this.initialize();
  }

  private initialize(): void {
    try {
      if (!this.config.enabled) {
        return;
      }

      // Start batch processing for remote/localStorage outputs
      if (this.config.outputs.remote || this.config.outputs.localStorage) {
        this.startBatchProcessing();
      }

      // Handle page unload - flush remaining logs
      if (typeof window !== 'undefined') {
        window.addEventListener('beforeunload', () => {
          this.flush();
        });

        // Handle visibility change (when tab becomes hidden)
        document.addEventListener('visibilitychange', () => {
          if (document.hidden) {
            this.flush();
          }
        });
      }
    } catch (error) {
      // Fallback to console if initialization fails
      console.error('Logger initialization failed:', error);
    }
  }

  private shouldLog(level: LogLevel): boolean {
    if (!this.config.enabled) {
      return false;
    }
    return LOG_LEVELS[level] >= LOG_LEVELS[this.config.level];
  }

  private createLogEntry(level: LogLevel, message: string, data?: any, filepath?: string): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
      filepath,
      loggerId: this.loggerId,
      sessionId: this.sessionId
    };
  }

  private formatConsoleMessage(entry: LogEntry): string {
    let parts: string[] = [];

    // Add timestamp if enabled
    if (this.config.showTimestamp) {
      const time = new Date(entry.timestamp).toLocaleTimeString();
      parts.push(`[${time}]`);
    }

    // Add log level if enabled
    if (this.config.showLogLevel) {
      parts.push(`[${entry.level.toUpperCase()}]`);
    }

    // Add filepath if enabled and available
    if (this.config.showFilePath && entry.filepath) {
      parts.push(`[${entry.filepath}]`);
    }

    // Add message
    parts.push(entry.message);

    return parts.join(' ');
  }

  private outputToConsole(entry: LogEntry): void {
    if (!this.config.outputs.console) {
      return;
    }

    const message = this.formatConsoleMessage(entry);
    const style = this.config.colorize ? `color: ${LOG_COLORS[entry.level]}` : '';

    // Handle grouped logs
    const consoleMethod = this.getConsoleMethod(entry.level);

    if (this.config.colorize && style) {
      consoleMethod(`%c${message}`, style, entry.data || '');
    } else {
      consoleMethod(message, entry.data || '');
    }
  }

  private getConsoleMethod(level: LogLevel): Console['log'] {
    switch (level) {
      case 'debug':
        return console.debug;
      case 'info':
        return console.info;
      case 'warn':
        return console.warn;
      case 'error':
      case 'critical':
        return console.error;
      default:
        return console.log;
    }
  }

  private outputToLocalStorage(entry: LogEntry): void {
    if (!this.config.outputs.localStorage || typeof window === 'undefined') {
      return;
    }

    try {
      const storageKey = 'app_logs';
      const existingLogs = localStorage.getItem(storageKey);
      let logs: LogEntry[] = existingLogs ? JSON.parse(existingLogs) : [];

      // Add new log
      logs.push(entry);

      // Maintain size limit
      const maxSize = this.config.maxStorageSize || 5242880; // Use maxStorageSize from config
      const logsString = JSON.stringify(logs);
      if (logsString.length > maxSize) {
        // Remove oldest logs until under size limit
        while (logs.length > 0 && JSON.stringify(logs).length > maxSize) {
          logs.shift();
        }
      }

      localStorage.setItem(storageKey, JSON.stringify(logs));
    } catch (error) {
      // localStorage might be full or disabled, fallback to console
      console.warn('Failed to write to localStorage:', error);
    }
  }

  private async outputToRemote(entries: LogEntry[]): Promise<void> {
    if (!this.config.outputs.remote || !this.config.remoteEndpoint) {
      return;
    }

    try {
      const response = await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: entries,
          loggerId: this.loggerId,
          sessionId: this.sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      // If remote logging fails, don't throw error - just log to console in development
      if (import.meta.env.MODE === 'development') {
        console.warn('Remote logging failed:', error);
      }
    }
  }

  private log(level: LogLevel, message: string, data?: any, filepath?: string): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry = this.createLogEntry(level, message, data, filepath);

    // Output to console immediately
    this.outputToConsole(entry);

    // Queue for localStorage and remote (batched)
    if (this.config.outputs.localStorage || this.config.outputs.remote) {
      this.logQueue.push(entry);
      this.outputToLocalStorage(entry); // localStorage is immediate, not batched
    }

    // Force flush for critical and error levels
    if (level === 'critical' || level === 'error') {
      this.flush();
    }
  }

  private startBatchProcessing(): void {
    this.batchTimer = setInterval(() => {
      if (this.logQueue.length >= this.config.batchSize) {
        this.processBatch();
      }
    }, this.config.batchInterval);
  }

  private processBatch(): void {
    if (this.logQueue.length === 0) {
      return;
    }

    const batch = [...this.logQueue];
    this.logQueue = [];

    // Send to remote endpoint
    if (this.config.outputs.remote) {
      this.outputToRemote(batch).catch(() => {
        // If remote fails, we already logged to console/localStorage
      });
    }
  }

  // Public API

  /**
   * Log debug message (most verbose level)
   */
  debug(message: string, data?: any, filepath?: string): void {
    this.log('debug', message, data, filepath);
  }

  /**
   * Log informational message
   */
  info(message: string, data?: any, filepath?: string): void {
    this.log('info', message, data, filepath);
  }

  /**
   * Log warning message
   */
  warn(message: string, data?: any, filepath?: string): void {
    this.log('warn', message, data, filepath);
  }

  /**
   * Log error message
   */
  error(message: string, data?: any, filepath?: string): void {
    this.log('error', message, data, filepath);
  }

  /**
   * Log critical error message (highest priority)
   */
  critical(message: string, data?: any, filepath?: string): void {
    this.log('critical', message, data, filepath);
  }

  /**
   * Conditional debug logging
   */
  debugIf(condition: boolean, message: string, data?: any, filepath?: string): void {
    if (condition) {
      this.debug(message, data, filepath);
    }
  }

  /**
   * Conditional info logging
   */
  infoIf(condition: boolean, message: string, data?: any, filepath?: string): void {
    if (condition) {
      this.info(message, data, filepath);
    }
  }

  /**
   * Start a new log group
   */
  group(name: string, collapsed: boolean = false): void {
    if (!this.shouldLog('debug')) {
      return;
    }

    this.groupStack.push({ name, collapsed });

    if (this.config.outputs.console) {
      if (collapsed && console.groupCollapsed) {
        console.groupCollapsed(name);
      } else if (console.group) {
        console.group(name);
      }
    }
  }

  /**
   * End the current log group
   */
  groupEnd(): void {
    if (!this.shouldLog('debug')) {
      return;
    }

    if (this.groupStack.length > 0) {
      this.groupStack.pop();

      if (this.config.outputs.console && console.groupEnd) {
        console.groupEnd();
      }
    }
  }

  /**
   * Start timing with a label
   */
  time(label: string): void {
    if (!this.shouldLog('debug')) {
      return;
    }

    this.timers.set(label, {
      label,
      startTime: performance.now()
    });

    if (this.config.outputs.console && console.time) {
      console.time(label);
    }
  }

  /**
   * End timing and log the duration
   */
  timeEnd(label: string): void {
    if (!this.shouldLog('debug')) {
      return;
    }

    const timer = this.timers.get(label);
    if (timer) {
      const duration = performance.now() - timer.startTime;
      this.debug(`Timer ${label}: ${duration.toFixed(2)}ms`);
      this.timers.delete(label);
    }

    if (this.config.outputs.console && console.timeEnd) {
      console.timeEnd(label);
    }
  }

  /**
   * Force flush all queued logs
   */
  flush(): void {
    this.processBatch();
  }

  /**
   * Clear localStorage logs
   */
  clearStoredLogs(): void {
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('app_logs');
      } catch (error) {
        console.warn('Failed to clear stored logs:', error);
      }
    }
  }

  /**
   * Get stored logs from localStorage
   */
  getStoredLogs(): LogEntry[] {
    if (typeof window === 'undefined') {
      return [];
    }

    try {
      const logs = localStorage.getItem('app_logs');
      return logs ? JSON.parse(logs) : [];
    } catch (error) {
      console.warn('Failed to retrieve stored logs:', error);
      return [];
    }
  }

  /**
   * Download logs as a file
   */
  downloadLogs(): void {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      const logs = this.getStoredLogs();
      const content = JSON.stringify(logs, null, 2);
      const blob = new Blob([content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = `app_logs_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      this.error('Failed to download logs', error);
    }
  }

  /**
   * Update logger configuration
   */
  updateConfig(newConfig: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...newConfig };

    // Restart batch processing if needed
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }

    if (this.config.enabled && (this.config.outputs.remote || this.config.outputs.localStorage)) {
      this.startBatchProcessing();
    }
  }

  /**
   * Get current logger metadata
   */
  getMetadata(): LoggerMetadata {
    return {
      loggerId: this.loggerId,
      sessionId: this.sessionId,
      queueSize: this.logQueue.length,
      config: { ...this.config }
    };
  }

  /**
   * Destroy logger and cleanup resources
   */
  destroy(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }

    this.flush();
    this.timers.clear();
    this.groupStack = [];
    this.logQueue = [];
  }
}

// Create and export singleton instance
const logger = new ComprehensiveLogger();

// Export the instance as default
export default logger;

// Also export the class for testing and custom instances
export { ComprehensiveLogger };

// Export types for external use
export type { LogLevel, LogEntry, LoggerConfig, LoggerMetadata } from '../types/logger.types';