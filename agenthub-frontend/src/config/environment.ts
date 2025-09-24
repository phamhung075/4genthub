/**
 * Environment Configuration
 * Centralizes all environment variable access
 * Ensures no hardcoded values in production
 */

// Note: Cannot import logger here due to circular dependency
// logger.config.ts depends on this file for API_BASE_URL

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

// Application Configuration
export const APP_NAME = getEnvVar('VITE_APP_NAME', 'agenthub');

// Keycloak Configuration
export const KEYCLOAK_URL = getEnvVar('VITE_KEYCLOAK_URL', '');
export const KEYCLOAK_REALM = getEnvVar('VITE_KEYCLOAK_REALM', '');
export const KEYCLOAK_CLIENT_ID = getEnvVar('VITE_KEYCLOAK_CLIENT_ID', '');

// WebSocket Configuration
export const WS_URL = getEnvVar('VITE_WS_URL', '');
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
  console.debug('Environment Configuration:', {
    API_BASE_URL,
    ENVIRONMENT,
    DEBUG_MODE,
    APP_NAME,
    WS_URL,
    WS_MAX_RECONNECT_ATTEMPTS,
    WS_RECONNECT_DELAY,
    WS_AI_BUFFER_TIMEOUT,
    WS_MAX_RECONNECT_DELAY,
    WS_HEARTBEAT_INTERVAL,
    configuredApiUrl: configuredApiUrl,
    wasUpgraded: configuredApiUrl !== API_BASE_URL
  });

  // Log if URL was auto-upgraded to HTTPS
  if (configuredApiUrl !== API_BASE_URL) {
    console.info('API URL auto-upgraded from HTTP to HTTPS for mixed content security');
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