/**
 * Logger Types
 * Type definitions for the comprehensive frontend logger system
 */

// =============================================================================
// Log Levels and Constants
// =============================================================================

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'critical';

export const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  critical: 4
};

export const LOG_COLORS: Record<LogLevel, string> = {
  debug: '#6B7280',    // Gray
  info: '#3B82F6',     // Blue
  warn: '#F59E0B',     // Amber
  error: '#EF4444',    // Red
  critical: '#DC2626'  // Dark Red
};

// =============================================================================
// Core Logger Types
// =============================================================================

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  filepath?: string;
  loggerId: string;
  sessionId: string;
}

export interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  showTimestamp: boolean;
  outputs: {
    console: boolean;
    localStorage: boolean;
    remote: boolean;
  };
  remoteEndpoint?: string;
  batchSize: number;
  batchInterval: number;
  maxStorageEntries: number;
}

export interface LoggerMetadata {
  loggerId: string;
  sessionId: string;
  queueSize: number;
  config: LoggerConfig;
}

export interface TimerEntry {
  startTime: number;
  label: string;
}

export interface LoggerGroup {
  name: string;
  startTime: number;
  collapsed: boolean;
}