/**
 * Logger configuration based on environment variables
 * All configuration can be controlled via .env files using REACT_APP_LOG_* variables
 */

import { LoggerConfig, LogLevel } from '../types/logger.types';

/**
 * Safe access to environment variables that works in both build time and runtime
 * In production builds, these are replaced by actual values during build
 */
const getEnvVar = (key: string): string | undefined => {
  // In React, process.env is replaced at build time
  // We need to check if we're in a Node environment or browser
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key];
  }
  // Fallback for browser environment - these should be replaced at build time
  // @ts-ignore
  return typeof window !== 'undefined' && window._env_ ? window._env_[key] : undefined;
};

/**
 * Parse boolean values from environment variables
 * Accepts: "true", "1", "yes", "on" as true (case-insensitive)
 */
const getEnvBoolean = (key: string, defaultValue: boolean): boolean => {
  const value = getEnvVar(key);
  if (value === undefined) return defaultValue;
  return ['true', '1', 'yes', 'on'].includes(value.toLowerCase());
};

/**
 * Parse log level from environment variable with validation
 */
const getEnvLogLevel = (): LogLevel => {
  const level = getEnvVar('REACT_APP_LOG_LEVEL')?.toLowerCase();
  const validLevels: LogLevel[] = ['debug', 'info', 'warn', 'error', 'critical'];
  return validLevels.includes(level as LogLevel) ? (level as LogLevel) : 'info';
};

/**
 * Parse integer values from environment variables
 */
const getEnvInteger = (key: string, defaultValue: number): number => {
  const value = getEnvVar(key);
  if (value === undefined) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
};

/**
 * Main logger configuration - reads all settings from environment variables
 * Falls back to sensible defaults if environment variables are not set
 */
export const loggerConfig: LoggerConfig = {
  // Core logger settings
  enabled: getEnvBoolean('REACT_APP_LOG_ENABLED', true),
  level: getEnvLogLevel(),

  // Display options
  showTimestamp: getEnvBoolean('REACT_APP_LOG_SHOW_TIMESTAMP', true),
  showLogLevel: getEnvBoolean('REACT_APP_LOG_SHOW_LEVEL', true),
  showFilePath: getEnvBoolean('REACT_APP_LOG_SHOW_FILE_PATH', false),
  colorize: getEnvBoolean('REACT_APP_LOG_COLORIZE', true),

  // Output destinations
  outputs: {
    console: getEnvBoolean('REACT_APP_LOG_TO_CONSOLE', true),
    localStorage: getEnvBoolean('REACT_APP_LOG_TO_LOCALSTORAGE', false),
    remote: getEnvBoolean('REACT_APP_LOG_TO_REMOTE', false),
  },

  // Storage and batching configuration
  maxStorageSize: getEnvInteger('REACT_APP_LOG_MAX_STORAGE_SIZE', 5242880), // 5MB default
  batchSize: getEnvInteger('REACT_APP_LOG_BATCH_SIZE', 10),
  batchInterval: getEnvInteger('REACT_APP_LOG_BATCH_INTERVAL', 5000), // 5 seconds

  // Remote logging endpoint
  remoteEndpoint: getEnvVar('REACT_APP_LOG_REMOTE_ENDPOINT') || 'http://localhost:8000/api/logs/frontend'
};

/**
 * Get configuration for different environments
 * This maintains backward compatibility while allowing full customization via environment variables
 */
export const getLoggerConfig = (): LoggerConfig => {
  // If environment variables are set, they override all defaults
  // This allows fine-grained control per environment
  return loggerConfig;
};

/**
 * Environment-specific configurations for reference/testing
 * These are now just presets - actual config comes from environment variables
 */
export const environmentPresets = {
  development: {
    REACT_APP_LOG_ENABLED: 'true',
    REACT_APP_LOG_LEVEL: 'debug',
    REACT_APP_LOG_SHOW_TIMESTAMP: 'true',
    REACT_APP_LOG_SHOW_LEVEL: 'true',
    REACT_APP_LOG_SHOW_FILE_PATH: 'true',
    REACT_APP_LOG_COLORIZE: 'true',
    REACT_APP_LOG_TO_CONSOLE: 'true',
    REACT_APP_LOG_TO_LOCALSTORAGE: 'true',
    REACT_APP_LOG_TO_REMOTE: 'false',
    REACT_APP_LOG_MAX_STORAGE_SIZE: '5242880',
    REACT_APP_LOG_BATCH_SIZE: '10',
    REACT_APP_LOG_BATCH_INTERVAL: '5000'
  },

  staging: {
    REACT_APP_LOG_ENABLED: 'true',
    REACT_APP_LOG_LEVEL: 'info',
    REACT_APP_LOG_SHOW_TIMESTAMP: 'true',
    REACT_APP_LOG_SHOW_LEVEL: 'true',
    REACT_APP_LOG_SHOW_FILE_PATH: 'false',
    REACT_APP_LOG_COLORIZE: 'false',
    REACT_APP_LOG_TO_CONSOLE: 'true',
    REACT_APP_LOG_TO_LOCALSTORAGE: 'true',
    REACT_APP_LOG_TO_REMOTE: 'true',
    REACT_APP_LOG_MAX_STORAGE_SIZE: '5242880',
    REACT_APP_LOG_BATCH_SIZE: '10',
    REACT_APP_LOG_BATCH_INTERVAL: '5000'
  },

  production: {
    REACT_APP_LOG_ENABLED: 'true',
    REACT_APP_LOG_LEVEL: 'warn',
    REACT_APP_LOG_SHOW_TIMESTAMP: 'true',
    REACT_APP_LOG_SHOW_LEVEL: 'true',
    REACT_APP_LOG_SHOW_FILE_PATH: 'false',
    REACT_APP_LOG_COLORIZE: 'false',
    REACT_APP_LOG_TO_CONSOLE: 'false',
    REACT_APP_LOG_TO_LOCALSTORAGE: 'false',
    REACT_APP_LOG_TO_REMOTE: 'true',
    REACT_APP_LOG_MAX_STORAGE_SIZE: '2097152', // 2MB for production
    REACT_APP_LOG_BATCH_SIZE: '20',
    REACT_APP_LOG_BATCH_INTERVAL: '10000'
  },

  test: {
    REACT_APP_LOG_ENABLED: 'false',
    REACT_APP_LOG_LEVEL: 'error',
    REACT_APP_LOG_SHOW_TIMESTAMP: 'false',
    REACT_APP_LOG_SHOW_LEVEL: 'true',
    REACT_APP_LOG_SHOW_FILE_PATH: 'false',
    REACT_APP_LOG_COLORIZE: 'false',
    REACT_APP_LOG_TO_CONSOLE: 'true',
    REACT_APP_LOG_TO_LOCALSTORAGE: 'false',
    REACT_APP_LOG_TO_REMOTE: 'false',
    REACT_APP_LOG_MAX_STORAGE_SIZE: '1048576', // 1MB for tests
    REACT_APP_LOG_BATCH_SIZE: '5',
    REACT_APP_LOG_BATCH_INTERVAL: '1000'
  }
};

/**
 * Debug helper: Log current configuration to console
 * Useful for debugging environment variable issues
 */
export const debugLoggerConfig = (): void => {
  if (getEnvVar('NODE_ENV') === 'development') {
    console.group('🔧 Logger Configuration Debug');
    console.log('Current config:', loggerConfig);
    console.log('Environment variables:');
    // In browser environment, we can't iterate over process.env
    // Log known environment variable keys instead
    const knownKeys = [
      'REACT_APP_LOG_ENABLED',
      'REACT_APP_LOG_LEVEL',
      'REACT_APP_LOG_SHOW_TIMESTAMP',
      'REACT_APP_LOG_SHOW_LEVEL',
      'REACT_APP_LOG_SHOW_FILE_PATH',
      'REACT_APP_LOG_COLORIZE',
      'REACT_APP_LOG_TO_CONSOLE',
      'REACT_APP_LOG_TO_LOCALSTORAGE',
      'REACT_APP_LOG_TO_REMOTE',
      'REACT_APP_LOG_MAX_STORAGE_SIZE',
      'REACT_APP_LOG_BATCH_SIZE',
      'REACT_APP_LOG_BATCH_INTERVAL',
      'REACT_APP_LOG_REMOTE_ENDPOINT'
    ];
    knownKeys.forEach(key => {
      const value = getEnvVar(key);
      if (value !== undefined) {
        console.log(`  ${key}=${value}`);
      }
    });
    console.groupEnd();
  }
};

// Legacy exports for backward compatibility
export const baseConfig = loggerConfig;
export const developmentConfig = loggerConfig;
export const stagingConfig = loggerConfig;
export const productionConfig = loggerConfig;
export const testConfig = loggerConfig;