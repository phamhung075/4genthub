/**
 * Safe logger export that provides the comprehensive logger system
 *
 * This file provides a simple, backward-compatible interface for importing
 * the logger throughout the application.
 */

import logger from './logger';

// Re-export the singleton logger instance
export default logger;

// Named export for explicit imports
export { logger };

// Re-export the class and types for advanced usage
export { ComprehensiveLogger } from './logger';
export type { LogLevel, LogEntry, LoggerConfig, LoggerMetadata } from './logger';