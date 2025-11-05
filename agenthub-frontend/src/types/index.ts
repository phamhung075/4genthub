/**
 * Type Definitions Index - Single Source of Truth
 *
 * Centralized barrel export for all TypeScript types and interfaces.
 * Import from here for consistency: `import { Task, TaskSummary } from '@/types'`
 *
 * Organization:
 * - Core entities (Task, Subtask, Project, Branch)
 * - Summary types (TaskSummary, SubtaskSummary)
 * - API response types (TaskResponse, etc.)
 * - Component types (props, state interfaces)
 * - Utility types (hooks, animations, websockets)
 *
 * @module types
 * @version 2.0
 */

// ============================================
// CORE ENTITY TYPES (Full data)
// ============================================
export * from './api.types';

// ============================================
// TASK & SUBTASK TYPES (Includes summaries)
// ============================================
export * from './taskTypes';
export * from './subtaskTypes';

// ============================================
// PROJECT TYPES
// ============================================
export * from './projectTypes';

// ============================================
// AGENT TYPES (User-Specific Agent System)
// ============================================
export * from './agentTypes';

// ============================================
// API SERVICE TYPES (Response wrappers)
// ============================================
export * from './serviceTypes';

// ============================================
// COMPONENT TYPES (Props, state interfaces)
// ============================================
export * from './componentTypes';

// ============================================
// UTILITY TYPES
// ============================================
export * from './hookTypes';
export * from './animationTypes';
export * from './websocketTypes';
export * from './authTypes';
export * from './logger.types';
export * from './context.types';
export * from './utilityTypes';
export * from './testTypes';

// ============================================
// TYPE VALIDATION (Runtime type checking)
// ============================================
// Note: Import validators separately to avoid circular dependencies
// Usage: import { validators } from '@/utils/typeValidation'