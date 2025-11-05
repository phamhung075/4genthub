/**
 * TDD Test Suite: Subtask Badge Display on Task Rows
 *
 * Phase 2 of TDD Analysis - Create Failing Tests
 *
 * Purpose: Document expected behavior of subtask badge display
 * Root Cause: TaskSummary type missing subtask_count field from backend
 *
 * Test Strategy:
 * 1. Verify badge displays when subtask_count > 0
 * 2. Verify badge hides when subtask_count === 0
 * 3. Verify badge shows correct count
 * 4. Verify badge updates when count changes
 *
 * Expected Failures (before fix):
 * - Tests will fail because TaskSummary doesn't have subtask_count property
 * - Component uses fullTask?.subtasks?.length (only available when expanded)
 *
 * Fix Requirements:
 * 1. Add subtask_count to TaskSummary interface (taskTypes.ts:39-49)
 * 2. Update TaskRowDesktop to use summary.subtask_count (TaskRowDesktop.tsx:44)
 * 3. Update TaskRowMobile to use summary.subtask_count
 */

import React from 'react';
import { render, screen } from './../../test-utils';
import { vi } from 'vitest';
import { TaskRowDesktop } from '../../../components/TaskRow/components/TaskRowDesktop';
import { TaskSummary } from '../../../types/taskTypes';

// Mock all UI components
vi.mock('../../../components/ui/badge', () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-testid="badge" data-variant={variant} className={className}>
      {children}
    </span>
  )
}));

vi.mock('../../../components/ui/button', () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}));

vi.mock('../../../components/ui/table', () => ({
  TableRow: ({ children, className, onMouseEnter, onMouseLeave }: any) => (
    <tr className={className} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}>
      {children}
    </tr>
  ),
  TableCell: ({ children, className, colSpan }: any) => (
    <td className={className} colSpan={colSpan}>
      {children}
    </td>
  )
}));

vi.mock('../../../components/ui/holographic-badges', () => ({
  HolographicStatusBadge: ({ status }: any) => <span data-testid="status-badge">{status}</span>,
  HolographicPriorityBadge: ({ priority }: any) => <span data-testid="priority-badge">{priority}</span>
}));

vi.mock('../../../components/ui/ProgressDisplay', () => ({
  ProgressDisplayEnhanced: () => <div data-testid="progress-display">Progress</div>
}));

vi.mock('../../../components/ClickableAssignees', () => ({
  default: () => <div data-testid="assignees">Assignees</div>
}));

vi.mock('../../../components/LazySubtaskList', () => ({
  default: () => <div data-testid="subtask-list">Subtasks</div>
}));

vi.mock('../../../components/TaskRow/components/TaskRowActions', () => ({
  TaskRowActions: () => <div data-testid="actions">Actions</div>
}));

vi.mock('../../../components/TaskRow/components/TaskCopyButtons', () => ({
  TaskCopyButtons: () => <div data-testid="copy-buttons">Copy</div>
}));

vi.mock('../../../components/TaskRow/hooks/useTaskRowState', () => ({
  useTaskRowState: () => ({
    getBaseClasses: vi.fn(() => '')
  })
}));

vi.mock('lucide-react', () => ({
  ChevronDown: () => <span>ChevronDown</span>,
  ChevronRight: () => <span>ChevronRight</span>
}));

describe('TaskRow - Subtask Badge Display (TDD Phase 2)', () => {
  const createTaskSummary = (overrides?: Partial<TaskSummary>): TaskSummary => ({
    id: 'task-1',
    title: 'Test Task',
    status: 'in_progress',
    priority: 'high',
    assignees: ['agent-1'],
    has_dependencies: false,
    has_context: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides
  });

  const defaultProps = {
    isExpanded: false,
    isLoading: false,
    fullTask: null,
    isHighlighted: false,
    isHovered: false,
    projectId: 'project-1',
    taskTreeId: 'branch-1',
    onToggleExpansion: vi.fn(),
    onOpenDialog: vi.fn(),
    onHover: vi.fn(),
    elementRef: { current: null } as React.RefObject<HTMLTableRowElement>,
    animationClass: ''
  };

  describe('Subtask Badge Visibility', () => {
    it('should display subtask count badge when task has subtasks', () => {
      // This test WILL FAIL until we add subtask_count to TaskSummary
      const taskWithSubtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 3,
        completed_subtasks: 1
      });

      render(
        <TaskRowDesktop
          summary={taskWithSubtasks}
          {...defaultProps}
        />
      );

      // EXPECTATION: Badge should display showing "3" subtasks
      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('3')
      );

      expect(subtaskBadge).toBeInTheDocument();
      expect(subtaskBadge).toHaveTextContent('3');
    });

    it('should NOT display subtask badge when subtask_count is 0', () => {
      const taskWithoutSubtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 0,
        completed_subtasks: 0
      });

      render(
        <TaskRowDesktop
          summary={taskWithoutSubtasks}
          {...defaultProps}
        />
      );

      // Badge should not appear for tasks without subtasks
      const badges = screen.queryAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.getAttribute('data-variant') === 'outline' &&
        badge.textContent?.match(/^\d+$/)
      );

      expect(subtaskBadge).toBeUndefined();
    });

    it('should NOT display subtask badge when subtask_count is undefined', () => {
      const taskWithUndefinedCount = createTaskSummary();
      // Note: subtask_count not set at all

      render(
        <TaskRowDesktop
          summary={taskWithUndefinedCount}
          {...defaultProps}
        />
      );

      const badges = screen.queryAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.getAttribute('data-variant') === 'outline' &&
        badge.textContent?.match(/^\d+$/)
      );

      expect(subtaskBadge).toBeUndefined();
    });
  });

  describe('Subtask Badge Content', () => {
    it('should show correct subtask count', () => {
      const taskWith5Subtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 5,
        completed_subtasks: 2
      });

      render(
        <TaskRowDesktop
          summary={taskWith5Subtasks}
          {...defaultProps}
        />
      );

      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('5')
      );

      expect(subtaskBadge).toBeInTheDocument();
      expect(subtaskBadge).toHaveTextContent('5');
    });

    it('should handle single subtask correctly', () => {
      const taskWithOneSubtask = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 1,
        completed_subtasks: 0
      });

      render(
        <TaskRowDesktop
          summary={taskWithOneSubtask}
          {...defaultProps}
        />
      );

      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('1')
      );

      expect(subtaskBadge).toBeInTheDocument();
      expect(subtaskBadge).toHaveTextContent('1');
    });
  });

  describe('Badge Display in Collapsed State', () => {
    it('should display badge even when task is NOT expanded', () => {
      // CRITICAL TEST: Badge should show in collapsed state using summary data
      const taskWithSubtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 4,
        completed_subtasks: 2
      });

      render(
        <TaskRowDesktop
          summary={taskWithSubtasks}
          {...defaultProps}
          isExpanded={false}
          fullTask={null} // No fullTask loaded yet
        />
      );

      // Badge should still display using summary.subtask_count
      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('4')
      );

      expect(subtaskBadge).toBeInTheDocument();
    });

    it('should use summary.subtask_count over fullTask.subtasks.length', () => {
      // Even if fullTask is available, should prefer summary.subtask_count
      const taskWithSubtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 3,
        completed_subtasks: 1
      });

      const fullTask = {
        ...taskWithSubtasks,
        subtasks: ['sub1', 'sub2'] // Only 2 loaded
      };

      render(
        <TaskRowDesktop
          summary={taskWithSubtasks}
          {...defaultProps}
          fullTask={fullTask}
        />
      );

      // Should show 3 (from summary) not 2 (from fullTask array)
      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('3')
      );

      expect(subtaskBadge).toBeInTheDocument();
    });
  });

  describe('Type Safety', () => {
    it('should handle subtask_count as number type', () => {
      const taskWithSubtasks = createTaskSummary({
        // @ts-expect-error - Testing type extension
        subtask_count: 10,
        completed_subtasks: 5
      });

      render(
        <TaskRowDesktop
          summary={taskWithSubtasks}
          {...defaultProps}
        />
      );

      const badges = screen.getAllByTestId('badge');
      const subtaskBadge = badges.find(badge =>
        badge.textContent?.includes('10')
      );

      expect(subtaskBadge).toBeInTheDocument();
    });
  });
});

/*
 * TEST EXECUTION EXPECTED RESULTS:
 *
 * BEFORE FIX (Current State):
 * - All tests WILL FAIL with TypeScript errors
 * - Error: Property 'subtask_count' does not exist on type 'TaskSummary'
 * - Component uses fullTask?.subtasks?.length fallback
 * - Badge only shows when task expanded (fullTask available)
 *
 * AFTER FIX (Expected State):
 * - Add subtask_count?: number to TaskSummary (taskTypes.ts:39-49)
 * - Add completed_subtasks?: number to TaskSummary
 * - Update component to use summary.subtask_count
 * - All tests should PASS
 * - Badge displays in both collapsed and expanded states
 *
 * FILES TO MODIFY:
 * 1. agenthub-frontend/src/types/taskTypes.ts:39-49
 *    - Add: subtask_count?: number;
 *    - Add: completed_subtasks?: number;
 *
 * 2. agenthub-frontend/src/components/TaskRow/components/TaskRowDesktop.tsx:44
 *    - Change: const subtaskCount = fullTask?.subtasks?.length ?? 0;
 *    - To: const subtaskCount = summary.subtask_count ?? fullTask?.subtasks?.length ?? 0;
 *
 * 3. agenthub-frontend/src/components/TaskRow/components/TaskRowMobile.tsx
 *    - Apply same fix as Desktop component
 */
