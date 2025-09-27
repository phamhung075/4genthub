/**
 * TypeScript interfaces and types for the logger system
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'critical';

export type LogOutput = 'console' | 'localStorage' | 'remote';

export interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  showTimestamp: boolean;
  showLogLevel: boolean;
  showFilePath: boolean;
  colorize: boolean;
  outputs: {
    console: boolean;
    localStorage: boolean;
    remote: boolean;
  };
  maxStorageSize: number;
  batchSize: number;
  batchInterval: number;
  remoteEndpoint?: string;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  filepath?: string;
  loggerId: string;
  sessionId: string;
}

export interface LoggerMetadata {
  loggerId: string;
  sessionId: string;
  queueSize: number;
  config: LoggerConfig;
}

export interface TimerEntry {
  label: string;
  startTime: number;
}

export interface LoggerGroup {
  name: string;
  collapsed: boolean;
}

export const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  critical: 4
} as const;

export const LOG_COLORS: Record<LogLevel, string> = {
  debug: '#6B7280',    // Gray
  info: '#3B82F6',     // Blue
  warn: '#F59E0B',     // Amber
  error: '#EF4444',    // Red
  critical: '#DC2626'  // Dark Red
} as const;