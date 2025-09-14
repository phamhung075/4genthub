/**
 * Environment Configuration
 * Centralizes all environment variable access
 * Ensures no hardcoded values in production
 */

// API Configuration
// Automatically upgrade to HTTPS if the page is served over HTTPS to avoid mixed content errors
const configuredApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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
export const ENVIRONMENT = import.meta.env.VITE_ENV || 'development';
export const IS_PRODUCTION = ENVIRONMENT === 'production';
export const IS_DEVELOPMENT = ENVIRONMENT === 'development';
export const IS_STAGING = ENVIRONMENT === 'staging';

// Debug Configuration
export const DEBUG_MODE = import.meta.env.VITE_DEBUG === 'true';

// Application Configuration
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'DhafnckMCP';

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
  console.log('Environment Configuration:', {
    API_BASE_URL,
    ENVIRONMENT,
    DEBUG_MODE,
    APP_NAME,
    configuredApiUrl: configuredApiUrl,
    wasUpgraded: configuredApiUrl !== API_BASE_URL
  });

  // Log if URL was auto-upgraded to HTTPS
  if (configuredApiUrl !== API_BASE_URL) {
    console.log('API URL auto-upgraded from HTTP to HTTPS for mixed content security');
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