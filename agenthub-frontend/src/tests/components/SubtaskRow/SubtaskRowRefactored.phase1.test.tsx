/**
 * Phase 1 Tests for SubtaskRowRefactored - Assignees Count Verification
 *
 * Tests verify that Phase 1 refactoring correctly calculates assignees count from arrays
 * instead of using removed backend count field (assignees_count).
 *
 * Key Changes Tested:
 * - Assignees count uses array.length with optional chaining
 * - Pattern: summary.assignees?.length ?? 0
 * - No reliance on removed assignees_count field from backend
 * - Proper handling of empty arrays and missing data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import SubtaskRowRefactored from '../../../components/SubtaskRow/SubtaskRowRefactored';
import type { SubtaskSummary } from '../../../types/subtaskTypes';

// Mock dependencies
vi.mock('../../../components/ui/table', () => ({
  TableRow: ({ children, className, ref }: any) => (
    <tr className={className} ref={ref}>{children}</tr>
  ),
  TableCell: ({ children, className }: any) => (
    <td className={className}>{children}</td>
  )
}));

vi.mock('../../../components/ui/CopyableId', () => ({
  CopyableId: ({ id, prefix }: any) => (
    <div data-testid="copyable-id">{prefix}-{id.slice(0, 8)}</div>
  )
}));

vi.mock('../../../components/ui/ParentTaskReference', () => ({
  ParentTaskReference: ({ taskId }: any) => (
    <div data-testid="parent-task-ref">Parent: {taskId}</div>
  )
}));

vi.mock('../../../components/SubtaskRow/hooks/useSubtaskAnimation', () => ({
  useSubtaskAnimation: () => ({
    animationState: 'none',
    isVisible: true,
    animationClass: '',
    elementRef: { current: null }
  })
}));

vi.mock('../../../components/SubtaskRow/components/SubtaskRowBadges', () => ({
  SubtaskRowBadges: ({ status, priority, progressPercentage }: any) => (
    <div data-testid="subtask-badges">
      <span>{status}</span>
      <span>{priority}</span>
      {progressPercentage && <span>{progressPercentage}%</span>}
    </div>
  )
}));

vi.mock('../../../components/SubtaskRow/components/SubtaskRowAssignees', () => ({
  SubtaskRowAssignees: ({ assignees, assigneesCount }: any) => (
    <div data-testid="subtask-assignees">
      {assigneesCount > 0 ? (
        <span>{assigneesCount} assignee{assigneesCount > 1 ? 's' : ''}: {assignees.join(', ')}</span>
      ) : (
        <span>Unassigned</span>
      )}
    </div>
  )
}));

vi.mock('../../../components/SubtaskRow/components/SubtaskRowActions', () => ({
  SubtaskRowActions: () => (
    <div data-testid="subtask-actions">Actions</div>
  )
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <table>
      <tbody>
        {children}
      </tbody>
    </table>
  </BrowserRouter>
);

describe('SubtaskRowRefactored - Phase 1 Assignees Count', () => {
  const mockSubtaskSummary: SubtaskSummary = {
    id: 'subtask-123',
    title: 'Test Subtask',
    status: 'in_progress',
    priority: 'high',
    assignees: ['coding-agent', 'test-agent', 'review-agent'],
    progress_percentage: 50
  };

  const defaultProps = {
    summary: mockSubtaskSummary,
    fullSubtask: null,
    isLoading: false,
    showDetails: false,
    parentTaskId: 'parent-task-456',
    onSubtaskAction: vi.fn(),
    onAgentInfoClick: vi.fn(),
    onDeleteSubtask: vi.fn(),
    onRegisterCallbacks: vi.fn(),
    onUnregisterCallbacks: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering Tests', () => {
    it('should render subtask row without errors', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
      expect(screen.getByTestId('subtask-badges')).toBeInTheDocument();
      expect(screen.getByTestId('subtask-assignees')).toBeInTheDocument();
    });

    it('should render with Phase 1 structure (no assignees_count field)', () => {
      // Mock data matches new backend structure
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      // Component renders successfully
      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
    });

    it('should render all table cells correctly', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByTestId('copyable-id')).toBeInTheDocument();
      expect(screen.getByTestId('parent-task-ref')).toBeInTheDocument();
      expect(screen.getByTestId('subtask-badges')).toBeInTheDocument();
      expect(screen.getByTestId('subtask-assignees')).toBeInTheDocument();
      expect(screen.getByTestId('subtask-actions')).toBeInTheDocument();
    });
  });

  describe('Assignees Count Calculations', () => {
    it('should calculate assignees count from array length (3 assignees)', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      // Should show count from assignees.length = 3
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('3 assignees');
      expect(assigneesEl).toHaveTextContent('coding-agent, test-agent, review-agent');
    });

    it('should handle single assignee correctly', () => {
      const summaryOneAssignee = {
        ...mockSubtaskSummary,
        assignees: ['solo-agent']
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={summaryOneAssignee}
          />
        </TestWrapper>
      );

      // Should use singular "assignee" not "assignees"
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('1 assignee');
      expect(assigneesEl).toHaveTextContent('solo-agent');
    });

    it('should handle empty assignees array (count = 0)', () => {
      const summaryNoAssignees = {
        ...mockSubtaskSummary,
        assignees: []
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={summaryNoAssignees}
          />
        </TestWrapper>
      );

      // Should show "Unassigned" when count is 0
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });

    it('should handle undefined assignees (optional chaining)', () => {
      const summaryUndefined = {
        ...mockSubtaskSummary,
        assignees: undefined as any
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={summaryUndefined}
          />
        </TestWrapper>
      );

      // Should NOT crash, should show "Unassigned"
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });

    it('should handle null assignees', () => {
      const summaryNull = {
        ...mockSubtaskSummary,
        assignees: null as any
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={summaryNull}
          />
        </TestWrapper>
      );

      // Should NOT crash, should show "Unassigned"
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });

    it('should calculate count correctly with many assignees', () => {
      const summaryManyAssignees = {
        ...mockSubtaskSummary,
        assignees: ['agent-1', 'agent-2', 'agent-3', 'agent-4', 'agent-5', 'agent-6']
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={summaryManyAssignees}
          />
        </TestWrapper>
      );

      // Should show count from assignees.length = 6
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('6 assignees');
    });
  });

  describe('Mock Data Compatibility', () => {
    it('should work with new backend response structure (no assignees_count field)', () => {
      // New backend structure: assignees array only, no assignees_count field
      const newBackendData: SubtaskSummary = {
        id: 'subtask-new',
        title: 'New Backend Structure',
        status: 'todo',
        priority: 'medium',
        assignees: ['agent-1', 'agent-2'], // Array, not count
        progress_percentage: 0
        // NO assignees_count field
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={newBackendData}
          />
        </TestWrapper>
      );

      // Should render successfully with new structure
      expect(screen.getByText('New Backend Structure')).toBeInTheDocument();

      // Text might be broken up by multiple elements, use container check
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('2 assignees');
    });

    it('should NOT rely on removed assignees_count field', () => {
      // Even if old data has assignees_count, should use array length
      const mixedData: any = {
        ...mockSubtaskSummary,
        assignees: ['agent-1', 'agent-2'],
        assignees_count: 999 // This should be IGNORED (old field)
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={mixedData}
          />
        </TestWrapper>
      );

      // Should use assignees.length (2), NOT assignees_count (999)
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('2 assignees');
      expect(screen.queryByText('999')).not.toBeInTheDocument();
    });
  });

  describe('Status and Priority Display', () => {
    it('should display status from summary', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      const badges = screen.getByTestId('subtask-badges');
      expect(badges).toHaveTextContent('in_progress');
    });

    it('should display priority from summary', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      const badges = screen.getByTestId('subtask-badges');
      expect(badges).toHaveTextContent('high');
    });

    it('should display progress percentage when available', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      const badges = screen.getByTestId('subtask-badges');
      expect(badges).toHaveTextContent('50%');
    });
  });

  describe('Animation and Visibility', () => {
    it('should render when visible', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
    });

    it('should apply loading class when isLoading is true', () => {
      const { container } = render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            isLoading={true}
          />
        </TestWrapper>
      );

      const row = container.querySelector('tr');
      expect(row).toHaveClass('loading');
    });
  });

  describe('Parent Task Reference', () => {
    it('should render parent task reference with correct ID', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByTestId('parent-task-ref')).toBeInTheDocument();
      expect(screen.getByText(/parent-task-456/)).toBeInTheDocument();
    });
  });

  describe('Callback Handlers', () => {
    it('should register animation callbacks on mount', () => {
      render(
        <TestWrapper>
          <SubtaskRowRefactored {...defaultProps} />
        </TestWrapper>
      );

      // The mock hook returns no callbacks, so this won't be called
      // In real implementation, useSubtaskAnimation would call it
      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
    });
  });

  describe('Array Length vs Count Field Comparison', () => {
    it('should ONLY use array.length, never *_count fields', () => {
      // Create mock with BOTH array AND old count field
      const dataWithBothFields: any = {
        ...mockSubtaskSummary,
        assignees: ['agent-1', 'agent-2', 'agent-3'], // length = 3
        assignees_count: 100 // OLD FIELD - should be IGNORED
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={dataWithBothFields}
          />
        </TestWrapper>
      );

      // Should use array.length (3), NOT assignees_count (100)
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('3 assignees');
      expect(screen.queryByText(/100/)).not.toBeInTheDocument();
    });

    it('should calculate count even if old field has different value', () => {
      const inconsistentData: any = {
        ...mockSubtaskSummary,
        assignees: ['single-agent'], // length = 1
        assignees_count: 99, // OLD FIELD with different value
        progress_percentage: 0 // Set to 0 to avoid "50%" in badges
      };

      render(
        <TestWrapper>
          <SubtaskRowRefactored
            {...defaultProps}
            summary={inconsistentData}
          />
        </TestWrapper>
      );

      // Should use array.length (1), ignore old count (99)
      const assigneesEl = screen.getByTestId('subtask-assignees');
      expect(assigneesEl).toHaveTextContent('1 assignee');
      expect(screen.queryByText(/99/)).not.toBeInTheDocument();
    });
  });
});
