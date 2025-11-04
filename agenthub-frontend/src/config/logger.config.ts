/**
 * Logger configuration based on environment variables
 * All configuration can be controlled via .env files using REACT_APP_LOG_* variables
 */

import { LoggerConfig, LogLevel } from '../types/logger.types';
import { API_BASE_URL } from './environment';

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
  remoteEndpoint: getEnvVar('VITE_LOG_REMOTE_ENDPOINT') || `${API_BASE_URL}/api/logs/frontend`
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
 * Debug helper: Log current configuration to console
 * Useful for debugging environment variable issues
 */
export const debugLoggerConfig = (): void => {
  // Always log in development mode for debugging
  // Check Vite's development mode flag
  const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development';

  console.group('🔧 Logger Configuration Debug');
  console.log('Environment Mode:', import.meta.env.MODE);
  console.log('Is Development:', isDev);
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
    console.log(`  ${key}=${value !== undefined ? value : 'undefined'}`);
  });
  console.groupEnd();
};