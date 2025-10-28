/**
 * WebSocket Message Validation Utility
 * Validates WebSocket messages against expected structure
 * Logs discrepancies for investigation
 */

import logger from './logger';
import { validateResponse, ValidationStats } from './responseValidator';
import type { WSMessage } from '../services/WebSocketClient';

export interface WSValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  timestamp: string;
  messageType: string;
}

/**
 * Validate WebSocket message structure
 */
export function validateWebSocketMessage(message: WSMessage): WSValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check message structure
  if (!message.type) {
    errors.push('message.type is missing');
  }

  if (!message.payload) {
    errors.push('message.payload is missing');
  } else {
    // Validate payload structure
    if (!message.payload.entity) {
      warnings.push('message.payload.entity is missing');
    }

    if (!message.payload.action) {
      warnings.push('message.payload.action is missing');
    }

    if (!message.payload.data) {
      warnings.push('message.payload.data is missing');
    } else {
      // Validate data structure
      const { data } = message.payload;

      // Check primary data
      if (data.primary) {
        const entity = message.payload.entity;
        let responseType: 'task' | 'subtask' | 'project' | 'branch' | 'unknown' = 'unknown';

        switch (entity) {
          case 'task':
            responseType = 'task';
            break;
          case 'subtask':
            responseType = 'subtask';
            break;
          case 'project':
            responseType = 'project';
            break;
          case 'branch':
          case 'git_branch':
            responseType = 'branch';
            break;
        }

        if (responseType !== 'unknown') {
          const result = validateResponse(
            data.primary,
            responseType,
            `ws://${entity}/${message.payload.action}`
          );

          if (!result.isValid) {
            errors.push(...result.errors.map(e => `primary.${e.field}: ${e.message}`));
          }

          warnings.push(...result.warnings.map(w => `primary.${w.field}: ${w.message}`));

          ValidationStats.record(result);
        }
      }

      // Validate cascade data if present
      if (data.cascade) {
        if (typeof data.cascade !== 'object') {
          errors.push('cascade data is not an object');
        } else {
          // Check cascade structure
          const cascadeLevels = ['parent_task', 'branch', 'project'];
          cascadeLevels.forEach(level => {
            if (data.cascade[level] && typeof data.cascade[level] !== 'object') {
              errors.push(`cascade.${level} is not an object`);
            }
          });
        }
      }
    }
  }

  // Check metadata
  if (!message.metadata) {
    warnings.push('message.metadata is missing');
  } else {
    if (!message.metadata.timestamp) {
      warnings.push('message.metadata.timestamp is missing');
    }
    if (!message.metadata.source) {
      warnings.push('message.metadata.source is missing');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    messageType: message.type || 'unknown'
  };
}

/**
 * Log WebSocket validation result
 */
export function logWSValidationResult(result: WSValidationResult, message: WSMessage) {
  if (!result.isValid) {
    logger.error('🚨 [WS Validation] Message FAILED', {
      messageType: result.messageType,
      timestamp: result.timestamp,
      errorCount: result.errors.length,
      warningCount: result.warnings.length,
      errors: result.errors,
      warnings: result.warnings,
      receivedMessage: message
    });
  } else if (result.warnings.length > 0) {
    logger.warn('⚠️ [WS Validation] Message has warnings', {
      messageType: result.messageType,
      timestamp: result.timestamp,
      warningCount: result.warnings.length,
      warnings: result.warnings
    });
  } else if (import.meta.env.DEV) {
    logger.debug('✅ [WS Validation] Message passed', {
      messageType: result.messageType,
      timestamp: result.timestamp
    });
  }
}

/**
 * WebSocket validation statistics
 */
export class WSValidationStats {
  private static stats = {
    totalMessages: 0,
    failedMessages: 0,
    warningCount: 0,
    errorsByType: new Map<string, number>(),
    messagesByType: new Map<string, number>()
  };

  static record(result: WSValidationResult) {
    this.stats.totalMessages++;

    // Track message type
    this.stats.messagesByType.set(
      result.messageType,
      (this.stats.messagesByType.get(result.messageType) || 0) + 1
    );

    if (!result.isValid) {
      this.stats.failedMessages++;
      this.stats.errorsByType.set(
        result.messageType,
        (this.stats.errorsByType.get(result.messageType) || 0) + 1
      );
    }

    this.stats.warningCount += result.warnings.length;
  }

  static getStats() {
    return {
      ...this.stats,
      messagesByType: Object.fromEntries(this.stats.messagesByType),
      errorsByType: Object.fromEntries(this.stats.errorsByType),
      failureRate: this.stats.totalMessages > 0
        ? (this.stats.failedMessages / this.stats.totalMessages * 100).toFixed(2) + '%'
        : '0%'
    };
  }

  static reset() {
    this.stats = {
      totalMessages: 0,
      failedMessages: 0,
      warningCount: 0,
      errorsByType: new Map(),
      messagesByType: new Map()
    };
  }

  static logSummary() {
    logger.info('📊 [WS Validation] Statistics Summary', this.getStats());
  }
}

// Enable stats logging in development
if (import.meta.env.DEV) {
  // Log stats every 30 seconds in development
  setInterval(() => {
    const stats = WSValidationStats.getStats();
    if (stats.totalMessages > 0) {
      WSValidationStats.logSummary();
    }
  }, 30000);
}
