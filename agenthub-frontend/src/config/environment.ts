/**
 * Environment Configuration
 * Centralizes all environment variable access
 * Ensures no hardcoded values in production
 */

import logger from '../utils/logger';

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

// Validate configuration in production
if (IS_PRODUCTION) {
  if (!import.meta.env.VITE_API_URL) {
    logger.error('CRITICAL: VITE_API_URL is not configured in production!');
    logger.error('Please configure VITE_API_URL in CapRover environment variables');
  }

  if (API_BASE_URL.includes('localhost')) {
    logger.warn('WARNING: API_BASE_URL contains localhost in production environment');
    logger.warn('Current URL:', API_BASE_URL);
    logger.warn('Please configure VITE_API_URL in CapRover to point to your production API');
  }
}

// Log configuration (only in development or debug mode)
if (IS_DEVELOPMENT || DEBUG_MODE) {
  logger.debug('Environment Configuration:', {
    API_BASE_URL,
    ENVIRONMENT,
    DEBUG_MODE,
    APP_NAME,
    configuredApiUrl: configuredApiUrl,
    wasUpgraded: configuredApiUrl !== API_BASE_URL
  });

  // Log if URL was auto-upgraded to HTTPS
  if (configuredApiUrl !== API_BASE_URL) {
    logger.info('API URL auto-upgraded from HTTP to HTTPS for mixed content security');
  }
}

// Export configuration object for easy access
export const config = {
  api: {
    baseUrl: API_BASE_URL,
    timeout: 30000, // 30 seconds
  },
  app: {
    name: APP_NAME,
    environment: ENVIRONMENT,
  },
  debug: DEBUG_MODE,
} as const;

export default config;