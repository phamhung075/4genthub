/**
 * Migration Helper for Logger System
 *
 * This file provides utilities to help with migrating console.* statements
 * to the new comprehensive logger system.
 */

import logger from './logger';

/**
 * Migration mapping guide for replacing console statements
 */
export const CONSOLE_MIGRATION_GUIDE = {
  'console.log': 'logger.info',
  'console.info': 'logger.info',
  'console.warn': 'logger.warn',
  'console.error': 'logger.error',
  'console.debug': 'logger.debug'
};

/**
 * Example migrations showing before/after patterns
 */
export const MIGRATION_EXAMPLES = {
  basic: {
    before: "console.log('User logged in', userData);",
    after: "logger.info('User logged in', { userData, component: 'ComponentName' });"
  },
  withContext: {
    before: "console.error('API call failed:', error);",
    after: "logger.error('API call failed', { error, component: 'ComponentName', endpoint: '/api/users' });"
  },
  conditional: {
    before: "if (isDev) console.debug('Debug info:', data);",
    after: "logger.debugIf(isDev, 'Debug info', { data, component: 'ComponentName' });"
  },
  grouped: {
    before: `
      console.group('User Authentication');
      console.log('Starting auth flow');
      console.log('Validating credentials');
      console.groupEnd();
    `,
    after: `
      logger.group('User Authentication');
      logger.info('Starting auth flow', { component: 'Auth' });
      logger.info('Validating credentials', { component: 'Auth' });
      logger.groupEnd();
    `
  },
  timing: {
    before: `
      console.time('api-call');
      // ... api call
      console.timeEnd('api-call');
    `,
    after: `
      logger.time('api-call');
      // ... api call
      logger.timeEnd('api-call');
    `
  }
};

/**
 * Best practices for using the new logger
 */
export const LOGGER_BEST_PRACTICES = {
  structure: {
    title: 'Always include component context',
    example: "logger.info('Action completed', { component: 'MyComponent', userId: 123 });"
  },

  levels: {
    title: 'Use appropriate log levels',
    guidelines: {
      debug: 'Detailed debugging information (filtered in production)',
      info: 'General informational messages',
      warn: 'Warning messages that don\'t stop execution',
      error: 'Error messages but app continues',
      critical: 'Critical errors that may cause app failure'
    }
  },

  performance: {
    title: 'Performance-aware logging',
    example: `
      // Good: Lazy evaluation
      logger.debugIf(isDevelopment, 'Complex data', {
        expensiveData: () => computeExpensiveData()
      });

      // Avoid: Always computing expensive data
      logger.debug('Complex data', { expensiveData: computeExpensiveData() });
    `
  },

  grouping: {
    title: 'Group related operations',
    example: `
      logger.group('User Registration Flow');
      logger.info('Validating user input', { component: 'Registration' });
      logger.info('Creating user account', { component: 'Registration' });
      logger.info('Sending welcome email', { component: 'Registration' });
      logger.groupEnd();
    `
  }
};

/**
 * Utility function to help identify console statements in code
 * This can be used in development to find remaining console statements
 */
export const findConsoleStatements = (codeString: string): string[] => {
  const consoleRegex = /console\.(log|info|warn|error|debug|group|groupEnd|time|timeEnd)\s*\(/g;
  const matches = [];
  let match;

  while ((match = consoleRegex.exec(codeString)) !== null) {
    matches.push(match[0]);
  }

  return matches;
};

/**
 * Migration helper function that suggests logger replacement
 */
export const suggestLoggerReplacement = (consoleStatement: string): string => {
  const consoleMethod = consoleStatement.match(/console\.(\w+)/)?.[1];

  if (!consoleMethod) {
    return 'Invalid console statement';
  }

  const loggerMethod = CONSOLE_MIGRATION_GUIDE[`console.${consoleMethod}` as keyof typeof CONSOLE_MIGRATION_GUIDE];

  if (!loggerMethod) {
    return `No direct replacement for console.${consoleMethod}`;
  }

  return `Replace with: ${loggerMethod}('message', { data, component: 'ComponentName' });`;
};

/**
 * Temporary console wrapper for gradual migration
 * Use this during migration to gradually replace console statements
 *
 * @deprecated Use logger directly instead
 */
export const migrationConsole = {
  log: (message: string, ...args: any[]) => {
    logger.info(message, { args, migration: true });
  },

  info: (message: string, ...args: any[]) => {
    logger.info(message, { args, migration: true });
  },

  warn: (message: string, ...args: any[]) => {
    logger.warn(message, { args, migration: true });
  },

  error: (message: string, ...args: any[]) => {
    logger.error(message, { args, migration: true });
  },

  debug: (message: string, ...args: any[]) => {
    logger.debug(message, { args, migration: true });
  }
};

export default {
  CONSOLE_MIGRATION_GUIDE,
  MIGRATION_EXAMPLES,
  LOGGER_BEST_PRACTICES,
  findConsoleStatements,
  suggestLoggerReplacement,
  migrationConsole
};