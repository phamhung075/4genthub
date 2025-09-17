/**
 * Safe logger export that can be used throughout the application
 */

import { FrontendLogger } from './logger';

// Create a singleton logger instance
let loggerInstance: FrontendLogger | null = null;

// Safe logger getter with fallback to console
export const getLogger = (): FrontendLogger | Console => {
  if (!loggerInstance) {
    try {
      loggerInstance = new FrontendLogger();
      return loggerInstance;
    } catch (error) {
      console.warn('Failed to create logger, using console fallback:', error);
      return console;
    }
  }
  return loggerInstance;
};

// Export logger instance for direct use
export const logger = getLogger();