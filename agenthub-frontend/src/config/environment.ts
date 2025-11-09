/**
 * Environment Configuration
 * Centralizes all environment variable access
 * Ensures no hardcoded values in production
 */

// INTENTIONAL: Using console.* in this file (environment configuration)
// Cannot import logger here due to circular dependency:
// - logger.config.ts depends on this file for API_BASE_URL
// - This file is loaded at app initialization before logger is available
// - Console usage here is for critical startup configuration errors/warnings only

// Helper to get runtime environment variable if available, fallback to build-time
function getEnvVar(key: string, defaultValue: string = ''): string {
  // Check runtime config first (injected by Docker at startup)
  if (typeof window !== 'undefined' && (window as any)._env_ && (window as any)._env_[key]) {
    const value = (window as any)._env_[key];
    // Ignore placeholder values and use runtime value if valid
    if (!value.startsWith('__') && !value.endsWith('__')) {
      return value;
    }
  }

  // Check build-time environment variable
  const buildTimeValue = import.meta.env[key] as string;

  // If build-time value is a placeholder, use default
  if (buildTimeValue && !buildTimeValue.startsWith('__') && !buildTimeValue.endsWith('__')) {
    return buildTimeValue;
  }

  // Return default value if neither runtime nor valid build-time value exists
  return defaultValue;
}

// API Configuration
// Automatically upgrade to HTTPS if the page is served over HTTPS to avoid mixed content errors
const configuredApiUrl = getEnvVar('VITE_API_URL', 'http://localhost:8000');
export const API_BASE_URL = (() => {
  // If we're running on HTTPS and the API URL is HTTP, upgrade it to HTTPS
  if (typeof window !== 'undefined' &&
      window.location.protocol === 'https:' &&
      configuredApiUrl.startsWith('http://')) {
    return configuredApiUrl.replace('http://', 'https://');
  }
  return configuredApiUrl;
})();

// Environment
export const ENVIRONMENT = getEnvVar('VITE_ENV', 'development');
export const IS_PRODUCTION = ENVIRONMENT === 'production';
export const IS_DEVELOPMENT = ENVIRONMENT === 'development';
export const IS_STAGING = ENVIRONMENT === 'staging';

// Debug Configuration
export const DEBUG_MODE = getEnvVar('VITE_DEBUG', 'false') === 'true';

// Authentication Configuration
export const DISABLE_AUTH = getEnvVar('VITE_DISABLE_AUTH', 'false') === 'true';

// Feature Flags
export const ENABLE_MARKETPLACE = getEnvVar('VITE_ENABLE_MARKETPLACE', 'true') === 'true';

// Application Configuration
export const APP_NAME = getEnvVar('VITE_APP_NAME', 'agenthub');

// WebSocket Configuration
// Auto-derive WebSocket URL from API URL in development if not explicitly configured
const getDefaultWebSocketUrl = (): string => {
  if (IS_DEVELOPMENT) {
    // Convert HTTP API URL to WebSocket URL for development
    return API_BASE_URL.replace(/^https?:/, 'ws:');
  }
  return '';
};

export const WS_URL = getEnvVar('VITE_WS_URL', getDefaultWebSocketUrl());
export const WS_MAX_RECONNECT_ATTEMPTS = parseInt(getEnvVar('VITE_WS_MAX_RECONNECT_ATTEMPTS', '5'), 10);
export const WS_RECONNECT_DELAY = parseInt(getEnvVar('VITE_WS_RECONNECT_DELAY', '1000'), 10);
export const WS_AI_BUFFER_TIMEOUT = parseInt(getEnvVar('VITE_WS_AI_BUFFER_TIMEOUT', '500'), 10);
export const WS_MAX_RECONNECT_DELAY = parseInt(getEnvVar('VITE_WS_MAX_RECONNECT_DELAY', '30000'), 10);
export const WS_HEARTBEAT_INTERVAL = parseInt(getEnvVar('VITE_WS_HEARTBEAT_INTERVAL', '30000'), 10);

// Validate configuration in production
if (IS_PRODUCTION) {
  if (!import.meta.env.VITE_API_URL) {
    console.error('CRITICAL: VITE_API_URL is not configured in production!');
    console.error('Please configure VITE_API_URL in CapRover environment variables');
  }

  if (API_BASE_URL.includes('localhost')) {
    console.warn('WARNING: API_BASE_URL contains localhost in production environment');
    console.warn('Current URL:', API_BASE_URL);
    console.warn('Please configure VITE_API_URL in CapRover to point to your production API');
  }
}

// Log configuration (only in development or debug mode)
if (IS_DEVELOPMENT || DEBUG_MODE) {
  // Enhanced debugging for WebSocket configuration
  console.info('🔧 DEBUG: Environment Configuration Analysis:');
  console.info('  - API_BASE_URL:', API_BASE_URL);
  console.info('  - VITE_WS_URL from getEnvVar:', getEnvVar('VITE_WS_URL', 'NOT_SET'));
  console.info('  - getDefaultWebSocketUrl():', getDefaultWebSocketUrl());
  console.info('  - Final WS_URL:', WS_URL);
  console.info('  - IS_DEVELOPMENT:', IS_DEVELOPMENT);
  console.info('  - DEBUG_MODE:', DEBUG_MODE);
  console.info('  - DISABLE_AUTH:', DISABLE_AUTH);
  console.info('  - ENABLE_MARKETPLACE:', ENABLE_MARKETPLACE);

  // Warn if authentication is disabled
  if (DISABLE_AUTH) {
    console.warn('⚠️  WARNING: Authentication is DISABLED (VITE_DISABLE_AUTH=true)');
    console.warn('⚠️  This should ONLY be used in local development!');
    console.warn('⚠️  Users can access the app without logging in.');
  }

  // Log if URL was auto-upgraded to HTTPS
  if (configuredApiUrl !== API_BASE_URL) {
    console.info('API URL auto-upgraded from HTTP to HTTPS for mixed content security');
  }

  // Log WebSocket configuration for debugging
  console.info(`🔌 WebSocket URL configured: ${WS_URL || 'NOT SET'}`);
  if (!WS_URL) {
    console.warn('⚠️ CRITICAL: WebSocket URL is not configured! Real-time features will not work.');
    console.warn('💡 Fix: Set VITE_WS_URL environment variable or ensure API_BASE_URL is set for auto-derivation');
    console.warn('🚨 DEBUG: Environment variable access test:');
    console.warn('  - window._env_:', typeof window !== 'undefined' ? (window as any)._env_ : 'not available');
    console.warn('  - import.meta.env.VITE_WS_URL:', import.meta.env.VITE_WS_URL);
    console.warn('  - import.meta.env:', import.meta.env);
  }
}

// Export configuration object for easy access
export const config = {
  api: {
    baseUrl: API_BASE_URL,
    timeout: 30000, // 30 seconds
  },
  websocket: {
    url: WS_URL,
    maxReconnectAttempts: WS_MAX_RECONNECT_ATTEMPTS,
    reconnectDelay: WS_RECONNECT_DELAY,
    aiBufferTimeout: WS_AI_BUFFER_TIMEOUT,
    maxReconnectDelay: WS_MAX_RECONNECT_DELAY,
    heartbeatInterval: WS_HEARTBEAT_INTERVAL,
  },
  app: {
    name: APP_NAME,
    environment: ENVIRONMENT,
  },
  debug: DEBUG_MODE,
} as const;

export default config;