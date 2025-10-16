/**
 * Type Validation Utilities
 *
 * Runtime validation to ensure backend responses match expected TypeScript interfaces.
 * Provides type guards and validation functions for critical types.
 *
 * @module utils/typeValidation
 */

import type { Task, Subtask, TaskSummary, SubtaskSummary } from '../types';
import logger from './logger';

/**
 * Validation result with detailed error information
 */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Type guard for Task
 *
 * Validates that an object conforms to the Task interface.
 * Checks required fields and types.
 */
export function isTask(obj: any): obj is Task {
  if (!obj || typeof obj !== 'object') return false;

  const required = ['id', 'title', 'status', 'priority', 'assignees_count', 'subtask_count', 'has_dependencies', 'has_context'];
  return required.every(field => field in obj);
}

/**
 * Type guard for TaskSummary
 *
 * Validates that an object conforms to the TaskSummary interface.
 * Used by LazyTaskList for lightweight validation.
 */
export function isTaskSummary(obj: any): obj is TaskSummary {
  if (!obj || typeof obj !== 'object') return false;

  const required = ['id', 'title', 'status', 'priority', 'subtask_count', 'assignees_count', 'has_dependencies', 'has_context'];
  return required.every(field => field in obj);
}

/**
 * Type guard for Subtask
 */
export function isSubtask(obj: any): obj is Subtask {
  if (!obj || typeof obj !== 'object') return false;

  const required = ['id', 'task_id', 'title', 'status', 'priority', 'assignees_count'];
  return required.every(field => field in obj);
}

/**
 * Type guard for SubtaskSummary
 */
export function isSubtaskSummary(obj: any): obj is SubtaskSummary {
  if (!obj || typeof obj !== 'object') return false;

  const required = ['id', 'title', 'status', 'priority', 'assignees_count'];
  return required.every(field => field in obj);
}

/**
 * Comprehensive Task validation with detailed error reporting
 *
 * @param obj - Object to validate
 * @param strict - If true, validate optional fields as well
 * @returns Validation result with errors and warnings
 */
export function validateTask(obj: any, strict: boolean = false): ValidationResult {
  const result: ValidationResult = {
    valid: true,
    errors: [],
    warnings: []
  };

  // Check required fields
  const requiredFields = {
    id: 'string',
    title: 'string',
    status: 'string',
    priority: 'string',
    assignees_count: 'number',
    subtask_count: 'number',
    has_dependencies: 'boolean',
    has_context: 'boolean'
  };

  Object.entries(requiredFields).forEach(([field, expectedType]) => {
    if (!(field in obj)) {
      result.errors.push(`Missing required field: ${field}`);
      result.valid = false;
    } else if (typeof obj[field] !== expectedType) {
      result.errors.push(`Field '${field}' has wrong type. Expected ${expectedType}, got ${typeof obj[field]}`);
      result.valid = false;
    }
  });

  // Check optional fields in strict mode
  if (strict) {
    if ('assignees' in obj && !Array.isArray(obj.assignees)) {
      result.warnings.push(`Field 'assignees' should be an array`);
    }

    if ('subtask_count' in obj && typeof obj.subtask_count === 'number') {
      if (obj.subtask_count < 0) {
        result.warnings.push(`Field 'subtask_count' should not be negative: ${obj.subtask_count}`);
      }
    }
  }

  // Check critical denormalization consistency
  if ('subtask_count' in obj && 'subtasks' in obj && Array.isArray(obj.subtasks)) {
    if (obj.subtask_count !== obj.subtasks.length) {
      result.warnings.push(
        `Denormalization inconsistency: subtask_count=${obj.subtask_count} but subtasks.length=${obj.subtasks.length}`
      );
    }
  }

  return result;
}

/**
 * Validate array of TaskSummary objects
 *
 * Used by LazyTaskList to validate API responses before rendering.
 * Logs validation errors for debugging.
 */
export function validateTaskSummaries(summaries: any[]): TaskSummary[] {
  if (!Array.isArray(summaries)) {
    logger.error('validateTaskSummaries: Expected array, got', typeof summaries);
    return [];
  }

  const validated: TaskSummary[] = [];
  const errors: string[] = [];

  summaries.forEach((summary, index) => {
    if (isTaskSummary(summary)) {
      validated.push(summary);
    } else {
      errors.push(`Invalid TaskSummary at index ${index}: ${JSON.stringify(summary)}`);
    }
  });

  if (errors.length > 0) {
    logger.warn(`TaskSummary validation found ${errors.length} invalid items:`, errors);
  }

  return validated;
}

/**
 * Validate array of SubtaskSummary objects
 *
 * Used by LazySubtaskList to validate API responses.
 */
export function validateSubtaskSummaries(summaries: any[]): SubtaskSummary[] {
  if (!Array.isArray(summaries)) {
    logger.error('validateSubtaskSummaries: Expected array, got', typeof summaries);
    return [];
  }

  const validated: SubtaskSummary[] = [];
  const errors: string[] = [];

  summaries.forEach((summary, index) => {
    if (isSubtaskSummary(summary)) {
      validated.push(summary);
    } else {
      errors.push(`Invalid SubtaskSummary at index ${index}: ${JSON.stringify(summary)}`);
    }
  });

  if (errors.length > 0) {
    logger.warn(`SubtaskSummary validation found ${errors.length} invalid items:`, errors);
  }

  return validated;
}

/**
 * Assert type at runtime with helpful error message
 *
 * Throws TypeError if validation fails. Use in development only.
 */
export function assertTask(obj: any, context: string = ''): asserts obj is Task {
  if (!isTask(obj)) {
    const validation = validateTask(obj, true);
    throw new TypeError(
      `Type assertion failed${context ? ` in ${context}` : ''}: Expected Task. ` +
      `Errors: ${validation.errors.join(', ')}`
    );
  }
}

/**
 * Safe type cast with fallback
 *
 * Returns the object as Task if valid, otherwise returns null.
 * Logs validation errors but doesn't throw.
 */
export function asTask(obj: any, logErrors: boolean = false): Task | null {
  if (isTask(obj)) {
    return obj;
  }

  if (logErrors) {
    const validation = validateTask(obj, true);
    logger.warn('asTask validation failed:', validation);
  }

  return null;
}

/**
 * Development-only strict validation
 *
 * In development mode, validates all API responses strictly.
 * In production, validation is skipped for performance.
 */
export function devValidateTask(obj: any, context: string = ''): Task {
  if (process.env.NODE_ENV === 'development') {
    const validation = validateTask(obj, true);

    if (!validation.valid) {
      logger.error(`[DEV] Task validation failed in ${context}:`, validation);
    }

    if (validation.warnings.length > 0) {
      logger.warn(`[DEV] Task validation warnings in ${context}:`, validation.warnings);
    }
  }

  return obj as Task;
}

// Export all type guards
export const typeGuards = {
  isTask,
  isTaskSummary,
  isSubtask,
  isSubtaskSummary
};

// Export all validators
export const validators = {
  validateTask,
  validateTaskSummaries,
  validateSubtaskSummaries,
  assertTask,
  asTask,
  devValidateTask
};
