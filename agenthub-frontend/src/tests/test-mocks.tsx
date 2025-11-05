/**
 * Test Mocks Library - Centralized Hook Mocks
 *
 * Provides reusable mock implementations for common hooks used across component tests.
 * Ensures consistency and reduces duplication in test files.
 *
 * Usage:
 *   import { mockUseBranchSummaries, mockUseEntityChanges } from './test-mocks';
 *   vi.mock('../hooks/useBranchSummaries', () => ({ useBranchSummaries: mockUseBranchSummaries }));
 */

import React from 'react';
import { vi } from 'vitest';
import type { BranchSummary } from '../types/api.types';

// ============================================================================
// Hook Mocks - useBranchSummaries
// ============================================================================

export interface MockBranchSummariesReturn {
  summaries: BranchSummary[];
  projects: any[];
  loading: boolean;
  error: string | null;
  refresh: ReturnType<typeof vi.fn>;
}

/**
 * Default mock for useBranchSummaries hook
 * Returns empty summaries with no loading state
 */
export const mockUseBranchSummaries = vi.fn((): MockBranchSummariesReturn => ({
  summaries: [],
  projects: [],
  loading: false,
  error: null,
  refresh: vi.fn(),
}));

/**
 * Create custom useBranchSummaries mock with specific data
 *
 * @param overrides - Partial return value to override defaults
 * @example
 * ```ts
 * const customMock = createBranchSummariesMock({
 *   summaries: [{ project_id: 'proj-1', branch_id: 'branch-1', task_count: 5 }],
 *   loading: false
 * });
 * vi.mock('../hooks/useBranchSummaries', () => ({ useBranchSummaries: customMock }));
 * ```
 */
export function createBranchSummariesMock(
  overrides: Partial<MockBranchSummariesReturn> = {}
) {
  return vi.fn(() => ({
    summaries: [],
    projects: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
    ...overrides,
  }));
}

// ============================================================================
// Hook Mocks - useEntityChanges
// ============================================================================

/**
 * Default mock for useEntityChanges hook
 * Returns empty array (no pending changes)
 */
export const mockUseEntityChanges = vi.fn(() => []);

/**
 * Create custom useEntityChanges mock with specific changes
 *
 * @param changes - Array of entity changes to return
 * @example
 * ```ts
 * const customMock = createEntityChangesMock([
 *   { type: 'task_updated', id: 'task-1', data: {...} }
 * ]);
 * vi.mock('../hooks/useChangeSubscription', () => ({ useEntityChanges: customMock }));
 * ```
 */
export function createEntityChangesMock(changes: any[] = []) {
  return vi.fn(() => changes);
}

// ============================================================================
// Hook Mocks - Toast Notifications
// ============================================================================

/**
 * Default mock for useErrorToast hook
 * Returns a no-op function
 */
export const mockUseErrorToast = vi.fn(() => vi.fn());

/**
 * Default mock for useSuccessToast hook
 * Returns a no-op function
 */
export const mockUseSuccessToast = vi.fn(() => vi.fn());

/**
 * Create spy-enabled toast mocks for assertions
 *
 * @returns Object with spy functions for error and success toasts
 * @example
 * ```ts
 * const toastMocks = createToastMocks();
 * vi.mock('../components/ui/toast', () => ({
 *   useErrorToast: () => toastMocks.error,
 *   useSuccessToast: () => toastMocks.success
 * }));
 *
 * // Later in test
 * expect(toastMocks.error).toHaveBeenCalledWith('Error message');
 * ```
 */
export function createToastMocks() {
  return {
    error: vi.fn(),
    success: vi.fn(),
  };
}

// ============================================================================
// API Mocks - Common Patterns
// ============================================================================

/**
 * Create mock for API functions with promise resolution
 *
 * @param resolveValue - Value to resolve with
 * @param shouldReject - Whether to reject instead of resolve
 * @example
 * ```ts
 * const mockListProjects = createApiMock([{ id: 'proj-1', name: 'Project 1' }]);
 * vi.mock('../api', () => ({ listProjects: mockListProjects }));
 * ```
 */
export function createApiMock<T>(resolveValue: T, shouldReject = false) {
  return vi.fn(() =>
    shouldReject
      ? Promise.reject(new Error('API Error'))
      : Promise.resolve(resolveValue)
  );
}

/**
 * Create mock for API functions that can be controlled per test
 *
 * @example
 * ```ts
 * const projectsApi = createControllableApiMock();
 * vi.mock('../api', () => ({ listProjects: projectsApi.fn }));
 *
 * // In test
 * projectsApi.resolveWith([{ id: 'proj-1' }]);
 * projectsApi.rejectWith(new Error('Failed'));
 * ```
 */
export function createControllableApiMock<T>() {
  const fn = vi.fn();

  return {
    fn,
    resolveWith: (value: T) => fn.mockResolvedValue(value),
    rejectWith: (error: Error) => fn.mockRejectedValue(error),
    reset: () => fn.mockReset(),
  };
}

// ============================================================================
// Component Mocks - Common Patterns
// ============================================================================

/**
 * Create mock component that renders children with test ID
 *
 * @param testId - Test ID for the mock component
 * @example
 * ```ts
 * vi.mock('../components/Dialog', () => ({
 *   default: createMockComponent('dialog')
 * }));
 * ```
 */
export function createMockComponent(testId: string) {
  return ({ children, ...props }: any) => (
    <div data-testid={testId} {...props}>
      {children}
    </div>
  );
}

/**
 * Create mock component with conditional rendering (for dialogs, modals, etc.)
 *
 * @param testId - Test ID for the mock component
 * @param openProp - Name of the prop that controls visibility (default: 'open')
 * @example
 * ```ts
 * vi.mock('../components/Dialog', () => ({
 *   default: createConditionalMockComponent('dialog', 'isOpen')
 * }));
 * ```
 */
export function createConditionalMockComponent(
  testId: string,
  openProp: string = 'open'
) {
  return ({ children, ...props }: any) =>
    props[openProp] ? (
      <div data-testid={testId} {...props}>
        {children}
      </div>
    ) : null;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Reset all mocks to their default state
 * Useful in beforeEach/afterEach hooks
 */
export function resetAllMocks() {
  mockUseBranchSummaries.mockClear();
  mockUseEntityChanges.mockClear();
  mockUseErrorToast.mockClear();
  mockUseSuccessToast.mockClear();
}

/**
 * Complete toast mock module for vi.mock()
 * Includes all exported functions from ui/toast
 *
 * @example
 * ```ts
 * vi.mock('../components/ui/toast', () => mockToastModule);
 * ```
 */
export const mockToastModule = {
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useToast: () => ({ toast: vi.fn() }),
  useSuccessToast: () => vi.fn(),
  useErrorToast: () => vi.fn(),
  Toast: ({ children }: any) => <div>{children}</div>,
  ToastAction: ({ children }: any) => <button>{children}</button>,
  ToastClose: () => <button>Close</button>,
  ToastDescription: ({ children }: any) => <div>{children}</div>,
  ToastTitle: ({ children }: any) => <div>{children}</div>,
  ToastViewport: () => <div />,
};

/**
 * Common mock data for tests
 */
export const mockData = {
  project: {
    id: 'proj-1',
    name: 'Test Project',
    description: 'Test Description',
    git_branchs: {},
  },
  branch: {
    id: 'branch-1',
    name: 'main',
    git_branch_name: 'main',
    project_id: 'proj-1',
  },
  task: {
    id: 'task-1',
    title: 'Test Task',
    status: 'todo' as const,
    priority: 'medium' as const,
    git_branch_id: 'branch-1',
  },
  branchSummary: {
    id: 'branch-1',
    project_id: 'proj-1',
    name: 'main',
    git_branch_name: 'main',
    task_count: 5,
    completed_tasks: 2,
    in_progress_tasks: 1,
    blocked_tasks: 0,
    todo_tasks: 2,
    progress_percentage: 40,
  } as BranchSummary,
};
