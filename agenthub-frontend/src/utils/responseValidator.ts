/**
 * Response Validation Utility
 * Validates API responses against TypeScript type definitions
 * Logs discrepancies between expected types and actual received data
 */

import logger from './logger';
import type {
  Task,
  Subtask,
  Project,
  GitBranch,
  Context,
} from '../types/api.types';

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  timestamp: string;
  endpoint: string;
}

export interface ValidationError {
  field: string;
  expected: string;
  actual: string;
  message: string;
}

export interface ValidationWarning {
  field: string;
  message: string;
}

/**
 * Check if value is a valid UUID
 */
function isValidUUID(value: any): boolean {
  if (typeof value !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(value);
}

/**
 * Check if value is a valid ISO 8601 datetime string
 */
function isValidISO8601(value: any): boolean {
  if (typeof value !== 'string') return false;
  const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$/;
  return isoRegex.test(value);
}

/**
 * Detect if response is in minimal/performance mode
 */
function isMinimalMode(data: any): boolean {
  // Check if this is a minimal response (missing typically-required fields)
  // Minimal mode responses omit project_id, subtasks, context_data, etc.
  return !data.project_id && !data.subtasks && !data.context_data;
}

/**
 * Validate Task response structure
 */
export function validateTask(data: any, endpoint: string): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];
  const minimal = isMinimalMode(data);

  // Log minimal mode detection for debugging
  if (minimal && import.meta.env.DEV) {
    logger.debug('🎯 [Response Validation] Minimal mode detected - relaxed validation applied', {
      endpoint,
      hasProjectId: !!data.project_id,
      hasSubtasks: !!data.subtasks,
      hasContextData: !!data.context_data
    });
  }

  // Required UUID fields (always required)
  const alwaysRequiredUUIDs = ['id', 'git_branch_id'];
  alwaysRequiredUUIDs.forEach(field => {
    if (!data[field]) {
      errors.push({
        field,
        expected: 'UUID string',
        actual: String(data[field]),
        message: `${field} is missing or null`
      });
    } else if (!isValidUUID(data[field])) {
      errors.push({
        field,
        expected: 'Valid UUID',
        actual: String(data[field]),
        message: `${field} is not a valid UUID`
      });
    }
  });

  // Optional UUID fields in minimal mode
  if (!minimal && !data.project_id) {
    errors.push({
      field: 'project_id',
      expected: 'UUID string',
      actual: String(data.project_id),
      message: 'project_id is missing or null'
    });
  } else if (data.project_id && !isValidUUID(data.project_id)) {
    errors.push({
      field: 'project_id',
      expected: 'Valid UUID',
      actual: String(data.project_id),
      message: 'project_id is not a valid UUID'
    });
  }

  // Required string field
  if (!data.title || typeof data.title !== 'string') {
    errors.push({
      field: 'title',
      expected: 'string',
      actual: typeof data.title,
      message: 'title is missing or not a string'
    });
  }

  // Assignees validation (more lenient in minimal mode)
  if (!minimal && (data.assignees === null || data.assignees === undefined)) {
    errors.push({
      field: 'assignees',
      expected: 'array',
      actual: String(data.assignees),
      message: 'assignees is null/undefined (should be empty array [])'
    });
  } else if (data.assignees !== undefined && data.assignees !== null && !Array.isArray(data.assignees)) {
    errors.push({
      field: 'assignees',
      expected: 'array',
      actual: typeof data.assignees,
      message: 'assignees is not an array'
    });
  } else if (Array.isArray(data.assignees)) {
    // Check each assignee has @ prefix
    data.assignees.forEach((assignee: any, index: number) => {
      if (typeof assignee !== 'string') {
        warnings.push({
          field: `assignees[${index}]`,
          message: `Assignee at index ${index} is not a string: ${typeof assignee}`
        });
      } else if (!assignee.startsWith('@')) {
        warnings.push({
          field: `assignees[${index}]`,
          message: `Assignee "${assignee}" missing @ prefix`
        });
      }
    });
  }

  // Timestamp fields
  const timestampFields = ['created_at', 'updated_at'];
  timestampFields.forEach(field => {
    if (!data[field]) {
      errors.push({
        field,
        expected: 'ISO 8601 datetime string',
        actual: String(data[field]),
        message: `${field} is missing`
      });
    } else if (!isValidISO8601(data[field])) {
      warnings.push({
        field,
        message: `${field} is not valid ISO 8601 format: ${data[field]}`
      });
    }
  });

  // updated_at should be >= created_at
  if (data.created_at && data.updated_at) {
    const created = new Date(data.created_at);
    const updated = new Date(data.updated_at);
    if (updated < created) {
      warnings.push({
        field: 'updated_at',
        message: `updated_at (${data.updated_at}) is before created_at (${data.created_at})`
      });
    }
  }

  // Subtasks array validation (only validate if not in minimal mode)
  if (!minimal) {
    // Allow null or array - both mean "no subtasks" or "subtasks not loaded"
    if (data.subtasks !== undefined && data.subtasks !== null && !Array.isArray(data.subtasks)) {
      errors.push({
        field: 'subtasks',
        expected: 'array or null',
        actual: typeof data.subtasks,
        message: 'subtasks must be an array or null'
      });
    }

    // Subtask count fields (only validate if subtasks array is present)
    if (typeof data.subtask_count === 'number' && Array.isArray(data.subtasks)) {
      if (data.subtask_count !== data.subtasks.length) {
        errors.push({
          field: 'subtask_count',
          expected: String(data.subtasks.length),
          actual: String(data.subtask_count),
          message: `subtask_count (${data.subtask_count}) doesn't match subtasks.length (${data.subtasks.length})`
        });
      }
    }

    // Completed subtasks count (only validate if subtasks array is present)
    if (typeof data.completed_subtasks === 'number' && Array.isArray(data.subtasks)) {
      const actualCompleted = data.subtasks.filter((s: any) => s.status === 'done' || s.status === 'completed').length;
      if (data.completed_subtasks !== actualCompleted) {
        errors.push({
          field: 'completed_subtasks',
          expected: String(actualCompleted),
          actual: String(data.completed_subtasks),
          message: `completed_subtasks (${data.completed_subtasks}) doesn't match actual completed count (${actualCompleted})`
        });
      }
    }

    // context_data validation (only in full mode)
    if (data.context_data === null) {
      warnings.push({
        field: 'context_data',
        message: 'context_data is null (expected empty object {})'
      });
    } else if (data.context_data !== undefined && typeof data.context_data !== 'object') {
      errors.push({
        field: 'context_data',
        expected: 'object',
        actual: typeof data.context_data,
        message: 'context_data is not an object'
      });
    }
  }

  // Progress percentage should be 0-100
  if (typeof data.progress_percentage === 'number') {
    if (data.progress_percentage < 0 || data.progress_percentage > 100) {
      errors.push({
        field: 'progress_percentage',
        expected: '0-100',
        actual: String(data.progress_percentage),
        message: `progress_percentage (${data.progress_percentage}) is out of range`
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    endpoint
  };
}

/**
 * Validate Subtask response structure
 */
export function validateSubtask(data: any, endpoint: string): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Required UUID fields
  if (!isValidUUID(data.id)) {
    errors.push({
      field: 'id',
      expected: 'Valid UUID',
      actual: String(data.id),
      message: 'id is missing or not a valid UUID'
    });
  }

  if (!isValidUUID(data.parent_task_id) && !isValidUUID(data.task_id)) {
    errors.push({
      field: 'parent_task_id/task_id',
      expected: 'Valid UUID',
      actual: `parent_task_id: ${data.parent_task_id}, task_id: ${data.task_id}`,
      message: 'Neither parent_task_id nor task_id is a valid UUID'
    });
  }

  // Required string field
  if (!data.title || typeof data.title !== 'string') {
    errors.push({
      field: 'title',
      expected: 'string',
      actual: typeof data.title,
      message: 'title is missing or not a string'
    });
  }

  // Timestamp fields
  const timestampFields = ['created_at', 'updated_at'];
  timestampFields.forEach(field => {
    if (!data[field]) {
      errors.push({
        field,
        expected: 'ISO 8601 datetime string',
        actual: String(data[field]),
        message: `${field} is missing`
      });
    } else if (!isValidISO8601(data[field])) {
      warnings.push({
        field,
        message: `${field} is not valid ISO 8601 format: ${data[field]}`
      });
    }
  });

  // Progress percentage should be 0-100
  if (typeof data.progress_percentage === 'number') {
    if (data.progress_percentage < 0 || data.progress_percentage > 100) {
      errors.push({
        field: 'progress_percentage',
        expected: '0-100',
        actual: String(data.progress_percentage),
        message: `progress_percentage (${data.progress_percentage}) is out of range`
      });
    }
  }

  // Assignees (if present) must be array
  if (data.assignees !== undefined && data.assignees !== null) {
    if (!Array.isArray(data.assignees)) {
      errors.push({
        field: 'assignees',
        expected: 'array',
        actual: typeof data.assignees,
        message: 'assignees is not an array'
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    endpoint
  };
}

/**
 * Validate Project response structure
 */
export function validateProject(data: any, endpoint: string): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Required UUID field
  if (!isValidUUID(data.id)) {
    errors.push({
      field: 'id',
      expected: 'Valid UUID',
      actual: String(data.id),
      message: 'id is missing or not a valid UUID'
    });
  }

  // Required string field
  if (!data.name || typeof data.name !== 'string') {
    errors.push({
      field: 'name',
      expected: 'string',
      actual: typeof data.name,
      message: 'name is missing or not a string'
    });
  }

  // Timestamp fields
  const timestampFields = ['created_at', 'updated_at'];
  timestampFields.forEach(field => {
    if (data[field] && !isValidISO8601(data[field])) {
      warnings.push({
        field,
        message: `${field} is not valid ISO 8601 format: ${data[field]}`
      });
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    endpoint
  };
}

/**
 * Validate BranchSummary response structure
 * Used for performance-optimized bulk summary endpoints
 */
export function validateBranchSummary(data: any, endpoint: string): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Required UUID fields
  if (!isValidUUID(data.id)) {
    errors.push({
      field: 'id',
      expected: 'Valid UUID',
      actual: String(data.id),
      message: 'id is missing or not a valid UUID'
    });
  }

  if (!isValidUUID(data.project_id)) {
    errors.push({
      field: 'project_id',
      expected: 'Valid UUID',
      actual: String(data.project_id),
      message: 'project_id is missing or not a valid UUID'
    });
  }

  // Required string field (name is always required in BranchSummary)
  if (!data.name || typeof data.name !== 'string') {
    errors.push({
      field: 'name',
      expected: 'string',
      actual: typeof data.name,
      message: 'name is missing or not a string'
    });
  }

  // git_branch_name is OPTIONAL in BranchSummary (unlike GitBranch entity)
  if (data.git_branch_name !== undefined && typeof data.git_branch_name !== 'string') {
    warnings.push({
      field: 'git_branch_name',
      message: `git_branch_name should be string if present, got ${typeof data.git_branch_name}`
    });
  }

  // Required task count field
  if (typeof data.task_count !== 'number') {
    errors.push({
      field: 'task_count',
      expected: 'number',
      actual: typeof data.task_count,
      message: 'task_count is missing or not a number'
    });
  }

  // progress_percentage should be 0-100
  if (typeof data.progress_percentage === 'number') {
    if (data.progress_percentage < 0 || data.progress_percentage > 100) {
      errors.push({
        field: 'progress_percentage',
        expected: '0-100',
        actual: String(data.progress_percentage),
        message: `progress_percentage (${data.progress_percentage}) is out of range`
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    endpoint
  };
}

/**
 * Validate GitBranch response structure
 */
export function validateGitBranch(data: any, endpoint: string): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Check if this is a DELETE response (has 'deleted' field)
  const isDeleteResponse = data.deleted === true;

  if (isDeleteResponse) {
    // DELETE responses only need to validate basic confirmation fields
    if (!isValidUUID(data.id)) {
      errors.push({
        field: 'id',
        expected: 'Valid UUID',
        actual: String(data.id),
        message: 'id is missing or not a valid UUID'
      });
    }

    // Validate success field exists
    if (typeof data.success !== 'boolean') {
      warnings.push({
        field: 'success',
        expected: 'boolean',
        actual: typeof data.success,
        message: 'success field should be a boolean'
      });
    }
  } else {
    // GET/POST responses need full entity validation
    // Required UUID fields
    const uuidFields = ['id', 'project_id'];
    uuidFields.forEach(field => {
      if (!isValidUUID(data[field])) {
        errors.push({
          field,
          expected: 'Valid UUID',
          actual: String(data[field]),
          message: `${field} is missing or not a valid UUID`
        });
      }
    });

    // Required string field
    if (!data.git_branch_name || typeof data.git_branch_name !== 'string') {
      errors.push({
        field: 'git_branch_name',
        expected: 'string',
        actual: typeof data.git_branch_name,
        message: 'git_branch_name is missing or not a string'
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    timestamp: new Date().toISOString(),
    endpoint
  };
}

/**
 * Log validation result
 */
export function logValidationResult(result: ValidationResult, data: any) {
  if (!result.isValid) {
    logger.error('🚨 [Response Validation] FAILED', {
      endpoint: result.endpoint,
      timestamp: result.timestamp,
      errorCount: result.errors.length,
      warningCount: result.warnings.length,
      errors: result.errors,
      warnings: result.warnings,
      receivedData: data
    });
  } else if (result.warnings.length > 0) {
    logger.warn('⚠️ [Response Validation] Warnings', {
      endpoint: result.endpoint,
      timestamp: result.timestamp,
      warningCount: result.warnings.length,
      warnings: result.warnings,
      receivedData: data
    });
  } else if (import.meta.env.DEV) {
    logger.debug('✅ [Response Validation] Passed', {
      endpoint: result.endpoint,
      timestamp: result.timestamp
    });
  }
}

/**
 * Main validation dispatcher
 */
export function validateResponse(
  data: any,
  type: 'task' | 'subtask' | 'project' | 'branch' | 'branch_summary' | 'context' | 'unknown',
  endpoint: string
): ValidationResult {
  switch (type) {
    case 'task':
      return validateTask(data, endpoint);
    case 'subtask':
      return validateSubtask(data, endpoint);
    case 'project':
      return validateProject(data, endpoint);
    case 'branch':
      return validateGitBranch(data, endpoint);
    case 'branch_summary':
      return validateBranchSummary(data, endpoint);
    default:
      return {
        isValid: true,
        errors: [],
        warnings: [],
        timestamp: new Date().toISOString(),
        endpoint
      };
  }
}

/**
 * Detect response type from URL
 */
export function detectResponseType(url: string): 'task' | 'subtask' | 'project' | 'branch' | 'branch_summary' | 'context' | 'unknown' {
  // CRITICAL: Check for bulk summaries BEFORE general branches check
  // This prevents BranchSummary objects from being validated as GitBranch entities
  if (url.includes('/branches/summaries/bulk')) return 'branch_summary';

  if (url.includes('/tasks/') || url.includes('/tasks?')) return 'task';
  if (url.includes('/subtasks/')) return 'subtask';
  if (url.includes('/projects/')) return 'project';
  if (url.includes('/branches/') || url.includes('/branch/')) return 'branch';
  if (url.includes('/contexts/') || url.includes('/context/')) return 'context';
  return 'unknown';
}

/**
 * Statistics tracker for validation results
 */
export class ValidationStats {
  private static stats = {
    totalValidations: 0,
    failedValidations: 0,
    warningCount: 0,
    errorsByField: new Map<string, number>(),
    errorsByEndpoint: new Map<string, number>()
  };

  static record(result: ValidationResult) {
    this.stats.totalValidations++;

    if (!result.isValid) {
      this.stats.failedValidations++;
    }

    this.stats.warningCount += result.warnings.length;

    result.errors.forEach(error => {
      this.stats.errorsByField.set(
        error.field,
        (this.stats.errorsByField.get(error.field) || 0) + 1
      );
      this.stats.errorsByEndpoint.set(
        result.endpoint,
        (this.stats.errorsByEndpoint.get(result.endpoint) || 0) + 1
      );
    });
  }

  static getStats() {
    return {
      ...this.stats,
      errorsByField: Object.fromEntries(this.stats.errorsByField),
      errorsByEndpoint: Object.fromEntries(this.stats.errorsByEndpoint),
      failureRate: this.stats.totalValidations > 0
        ? (this.stats.failedValidations / this.stats.totalValidations * 100).toFixed(2) + '%'
        : '0%'
    };
  }

  static reset() {
    this.stats = {
      totalValidations: 0,
      failedValidations: 0,
      warningCount: 0,
      errorsByField: new Map(),
      errorsByEndpoint: new Map()
    };
  }

  static logSummary() {
    logger.info('📊 [Response Validation] Statistics Summary', this.getStats());
  }
}

// Enable stats logging in development
if (import.meta.env.DEV) {
  // Log stats every 30 seconds in development
  setInterval(() => {
    const stats = ValidationStats.getStats();
    if (stats.totalValidations > 0) {
      ValidationStats.logSummary();
    }
  }, 30000);
}
