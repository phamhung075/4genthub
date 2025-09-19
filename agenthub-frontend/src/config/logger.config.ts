/**
 * Logger configuration based on environment variables
 * All configuration can be controlled via .env files using REACT_APP_LOG_* variables
 */

import { LoggerConfig, LogLevel } from '../types/logger.types';

/**
 * Safe access to environment variables that works in both build time and runtime
 * For Vite, import.meta.env is available in both development and production
 */
const getEnvVar = (key: string): string | undefined => {
  // In Vite, import.meta.env contains all environment variables
  // Check if we're in a Vite environment
  if (typeof window !== 'undefined' && import.meta?.env) {
    return import.meta.env[key];
  }
  // Fallback for Node.js environment (testing)
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key];
  }
  // Additional fallback for browser environment
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
  const level = getEnvVar('VITE_LOG_LEVEL')?.toLowerCase();
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
  enabled: getEnvBoolean('VITE_LOG_ENABLED', true),
  level: getEnvLogLevel(),

  // Display options
  showTimestamp: getEnvBoolean('VITE_LOG_SHOW_TIMESTAMP', true),
  showLogLevel: getEnvBoolean('VITE_LOG_SHOW_LEVEL', true),
  showFilePath: getEnvBoolean('VITE_LOG_SHOW_FILE_PATH', false),
  colorize: getEnvBoolean('VITE_LOG_COLORIZE', true),

  // Output destinations
  outputs: {
    console: getEnvBoolean('VITE_LOG_TO_CONSOLE', true),
    localStorage: getEnvBoolean('VITE_LOG_TO_LOCALSTORAGE', false),
    remote: getEnvBoolean('VITE_LOG_TO_REMOTE', false),
  },

  // Storage and batching configuration
  maxStorageSize: getEnvInteger('VITE_LOG_MAX_STORAGE_SIZE', 5242880), // 5MB default
  batchSize: getEnvInteger('VITE_LOG_BATCH_SIZE', 10),
  batchInterval: getEnvInteger('VITE_LOG_BATCH_INTERVAL', 5000), // 5 seconds

  // Remote logging endpoint
  remoteEndpoint: getEnvVar('VITE_LOG_REMOTE_ENDPOINT') || 'http://localhost:8000/api/logs/frontend'
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
    VITE_LOG_ENABLED: 'true',
    VITE_LOG_LEVEL: 'debug',
    VITE_LOG_SHOW_TIMESTAMP: 'true',
    VITE_LOG_SHOW_LEVEL: 'true',
    VITE_LOG_SHOW_FILE_PATH: 'true',
    VITE_LOG_COLORIZE: 'true',
    VITE_LOG_TO_CONSOLE: 'true',
    VITE_LOG_TO_LOCALSTORAGE: 'true',
    VITE_LOG_TO_REMOTE: 'false',
    VITE_LOG_MAX_STORAGE_SIZE: '5242880',
    VITE_LOG_BATCH_SIZE: '10',
    VITE_LOG_BATCH_INTERVAL: '5000'
  },

  staging: {
    VITE_LOG_ENABLED: 'true',
    VITE_LOG_LEVEL: 'info',
    VITE_LOG_SHOW_TIMESTAMP: 'true',
    VITE_LOG_SHOW_LEVEL: 'true',
    VITE_LOG_SHOW_FILE_PATH: 'false',
    VITE_LOG_COLORIZE: 'false',
    VITE_LOG_TO_CONSOLE: 'true',
    VITE_LOG_TO_LOCALSTORAGE: 'true',
    VITE_LOG_TO_REMOTE: 'true',
    VITE_LOG_MAX_STORAGE_SIZE: '5242880',
    VITE_LOG_BATCH_SIZE: '10',
    VITE_LOG_BATCH_INTERVAL: '5000'
  },

  production: {
    VITE_LOG_ENABLED: 'true',
    VITE_LOG_LEVEL: 'warn',
    VITE_LOG_SHOW_TIMESTAMP: 'true',
    VITE_LOG_SHOW_LEVEL: 'true',
    VITE_LOG_SHOW_FILE_PATH: 'false',
    VITE_LOG_COLORIZE: 'false',
    VITE_LOG_TO_CONSOLE: 'false',
    VITE_LOG_TO_LOCALSTORAGE: 'false',
    VITE_LOG_TO_REMOTE: 'true',
    VITE_LOG_MAX_STORAGE_SIZE: '2097152', // 2MB for production
    VITE_LOG_BATCH_SIZE: '20',
    VITE_LOG_BATCH_INTERVAL: '10000'
  },

  test: {
    VITE_LOG_ENABLED: 'false',
    VITE_LOG_LEVEL: 'error',
    VITE_LOG_SHOW_TIMESTAMP: 'false',
    VITE_LOG_SHOW_LEVEL: 'true',
    VITE_LOG_SHOW_FILE_PATH: 'false',
    VITE_LOG_COLORIZE: 'false',
    VITE_LOG_TO_CONSOLE: 'true',
    VITE_LOG_TO_LOCALSTORAGE: 'false',
    VITE_LOG_TO_REMOTE: 'false',
    VITE_LOG_MAX_STORAGE_SIZE: '1048576', // 1MB for tests
    VITE_LOG_BATCH_SIZE: '5',
    VITE_LOG_BATCH_INTERVAL: '1000'
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
      'VITE_LOG_REMOTE_ENDPOINT'
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