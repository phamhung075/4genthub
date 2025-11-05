/**
 * Phase 1 Tests for TaskRowMobile - Count Calculation Verification
 *
 * Tests verify that Phase 1 refactoring correctly calculates counts from arrays
 * instead of using removed backend count fields (subtask_count, assignees_count, dependency_count).
 *
 * Key Changes Tested:
 * - Count calculations use array.length with optional chaining
 * - Fallback chain: fullTask?.subtasks?.length ?? 0
 * - No reliance on removed emoji/count fields from backend
 * - Proper handling of empty arrays and missing data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from './../../../test-utils';
import { BrowserRouter } from 'react-router-dom';
import { TaskRowMobile } from '../../../../components/TaskRow/components/TaskRowMobile';
import type { TaskSummary } from '../../../../types/taskTypes';

// Mock dependencies
vi.mock('../../../../components/ui/badge', () => ({
  Badge: ({ children, variant, className, title }: any) => (
    <span data-testid="badge" data-variant={variant} className={className} title={title}>
      {children}
    </span>
  )
}));

vi.mock('../../../../components/ui/button', () => ({
  Button: ({ children, onClick, disabled, variant, size, className }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-variant={variant}
      data-size={size}
      className={className}
    >
      {children}
    </button>
  )
}));

vi.mock('../../../../components/ui/holographic-badges', () => ({
  HolographicStatusBadge: ({ status, size }: any) => (
    <span data-testid="status-badge" data-status={status} data-size={size}>
      {status}
    </span>
  ),
  HolographicPriorityBadge: ({ priority, size }: any) => (
    <span data-testid="priority-badge" data-priority={priority} data-size={size}>
      {priority}
    </span>
  )
}));

vi.mock('../../../../components/ui/ProgressDisplay', () => ({
  ProgressDisplayEnhanced: () => <div data-testid="progress-display">Progress</div>
}));

vi.mock('../../../../components/ClickableAssignees', () => ({
  default: ({ assignees }: any) => (
    <div data-testid="assignees">
      {assignees.join(', ')}
    </div>
  )
}));

vi.mock('../../../../components/LazySubtaskList', () => ({
  default: () => <div data-testid="subtask-list">SubtaskList</div>
}));

vi.mock('../../../../components/TaskRow/components/TaskRowActions', () => ({
  TaskRowActions: () => <div data-testid="task-actions">Actions</div>
}));

vi.mock('../../../../components/TaskRow/components/TaskCopyButtons', () => ({
  TaskCopyButtons: () => <div data-testid="copy-buttons">Copy</div>
}));

vi.mock('../../../../components/TaskRow/hooks/useTaskRowState', () => ({
  useTaskRowState: () => ({
    getBaseClasses: (isHighlighted: boolean, isHovered: boolean) =>
      `base ${isHighlighted ? 'highlighted' : ''} ${isHovered ? 'hovered' : ''}`
  })
}));

vi.mock('lucide-react', () => ({
  ChevronDown: () => <span data-testid="chevron-down">Down</span>,
  ChevronRight: () => <span data-testid="chevron-right">Right</span>
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('TaskRowMobile - Phase 1 Count Calculations', () => {
  const mockSummary: TaskSummary = {
    id: 'task-123',
    title: 'Test Task Mobile',
    status: 'in_progress',
    priority: 'high',
    assignees: ['coding-agent', 'test-agent'],
    has_dependencies: true,
    dependencies: ['dep-1', 'dep-2', 'dep-3'],
    subtasks: [{ id: 'sub-1' }, { id: 'sub-2' }] as any
  };

  const defaultProps = {
    summary: mockSummary,
    fullTask: null,
    isHighlighted: false,
    isHovered: false,
    isExpanded: false,
    isLoading: false,
    projectId: 'proj-1',
    taskTreeId: 'tree-1',
    onToggleExpansion: vi.fn(),
    onOpenDialog: vi.fn(),
    onHover: vi.fn(),
    elementRef: { current: null } as any,
    animationClass: ''
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering Tests', () => {
    it('should render mobile view without errors', () => {
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByText('Test Task Mobile')).toBeInTheDocument();
      expect(screen.getByTestId('status-badge')).toBeInTheDocument();
      expect(screen.getByTestId('priority-badge')).toBeInTheDocument();
    });

    it('should render with Phase 1 structure (no emoji/count fields)', () => {
      // Mock data matches new backend structure (no old fields)
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} />
        </TestWrapper>
      );

      // Component renders successfully with new structure
      expect(screen.getByText('Test Task Mobile')).toBeInTheDocument();
    });
  });

  describe('Subtask Count Calculations', () => {
    it('should calculate subtask count from fullTask.subtasks array', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: [{ id: 'sub-1' }, { id: 'sub-2' }, { id: 'sub-3' }]
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should show count from fullTask.subtasks.length = 3
      const subtaskBadge = screen.getByText('3 subtasks');
      expect(subtaskBadge).toBeInTheDocument();
    });

    it('should handle empty subtasks array (count = 0)', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: []
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should NOT render badge when count is 0
      expect(screen.queryByText(/subtasks/)).not.toBeInTheDocument();
    });

    it('should handle undefined subtasks (optional chaining)', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: undefined
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should NOT crash, should NOT show badge
      expect(screen.queryByText(/subtasks/)).not.toBeInTheDocument();
    });

    it('should handle null subtasks', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: null
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should NOT crash, should NOT show badge
      expect(screen.queryByText(/subtasks/)).not.toBeInTheDocument();
    });
  });

  describe('Dependency Count Calculations', () => {
    it('should calculate dependency count from fullTask.dependencies array', () => {
      const fullTask = {
        ...mockSummary,
        dependencies: ['dep-1', 'dep-2', 'dep-3', 'dep-4']
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should show count from dependencies.length = 4
      const depBadge = screen.getByText('4 deps');
      expect(depBadge).toBeInTheDocument();
    });

    it('should handle single dependency correctly', () => {
      const fullTask = {
        ...mockSummary,
        dependencies: ['dep-1']
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should use singular "dep" not "deps"
      expect(screen.getByText('1 dep')).toBeInTheDocument();
    });

    it('should handle empty dependencies array', () => {
      const summaryNoDeps = {
        ...mockSummary,
        has_dependencies: false,
        dependencies: []
      };

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} summary={summaryNoDeps} />
        </TestWrapper>
      );

      // Should NOT render dependency badge
      expect(screen.queryByText(/dep/)).not.toBeInTheDocument();
    });

    it('should handle undefined dependencies (optional chaining)', () => {
      const fullTask = {
        ...mockSummary,
        dependencies: undefined
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} fullTask={fullTask} />
        </TestWrapper>
      );

      // Should NOT crash
      expect(screen.getByText('Test Task Mobile')).toBeInTheDocument();
    });
  });

  describe('Assignees Handling', () => {
    it('should render assignees from summary', () => {
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} />
        </TestWrapper>
      );

      expect(screen.getByTestId('assignees')).toBeInTheDocument();
      expect(screen.getByText(/coding-agent, test-agent/)).toBeInTheDocument();
    });

    it('should handle empty assignees array', () => {
      const summaryNoAssignees = {
        ...mockSummary,
        assignees: []
      };

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} summary={summaryNoAssignees} />
        </TestWrapper>
      );

      // Should NOT crash, assignees component not rendered
      expect(screen.queryByTestId('assignees')).not.toBeInTheDocument();
    });

    it('should handle undefined assignees', () => {
      const summaryNoAssignees = {
        ...mockSummary,
        assignees: undefined as any
      };

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} summary={summaryNoAssignees} />
        </TestWrapper>
      );

      // Should NOT crash
      expect(screen.getByText('Test Task Mobile')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('should show loading spinner when isLoading is true', () => {
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} isLoading={true} />
        </TestWrapper>
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should show expand icon when not loading and not expanded', () => {
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} isLoading={false} isExpanded={false} />
        </TestWrapper>
      );

      expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
    });

    it('should show collapse icon when expanded', () => {
      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} isExpanded={true} />
        </TestWrapper>
      );

      expect(screen.getByTestId('chevron-down')).toBeInTheDocument();
    });
  });

  describe('Expanded State - Subtask List', () => {
    it('should render LazySubtaskList when expanded with fullTask', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: [{ id: 'sub-1' }]
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            fullTask={fullTask}
            isExpanded={true}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('subtask-list')).toBeInTheDocument();
    });

    it('should NOT render LazySubtaskList when not expanded', () => {
      const fullTask = {
        ...mockSummary,
        subtasks: [{ id: 'sub-1' }]
      } as any;

      render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            fullTask={fullTask}
            isExpanded={false}
          />
        </TestWrapper>
      );

      expect(screen.queryByTestId('subtask-list')).not.toBeInTheDocument();
    });

    it('should NOT render LazySubtaskList when expanded but no fullTask', () => {
      render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            fullTask={null}
            isExpanded={true}
          />
        </TestWrapper>
      );

      expect(screen.queryByTestId('subtask-list')).not.toBeInTheDocument();
    });
  });

  describe('Mock Data Compatibility', () => {
    it('should work with new backend response structure (no old fields)', () => {
      // New backend structure: arrays only, no count fields, no emoji fields
      const newBackendData: TaskSummary = {
        id: 'task-new',
        title: 'New Backend Structure',
        status: 'todo',
        priority: 'medium',
        assignees: ['agent-1'],
        has_dependencies: false,
        subtasks: [], // Array, not count
        dependencies: [] // Array, not count
        // NO priority_emoji, NO status_emoji, NO subtask_count, NO assignees_count
      };

      render(
        <TestWrapper>
          <TaskRowMobile {...defaultProps} summary={newBackendData} />
        </TestWrapper>
      );

      // Should render successfully with new structure
      expect(screen.getByText('New Backend Structure')).toBeInTheDocument();
    });
  });

  describe('Animation Classes', () => {
    it('should apply animation class when provided', () => {
      const { container } = render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            animationClass="task-updating-animation"
          />
        </TestWrapper>
      );

      const mobileCard = container.querySelector('.task-updating-animation');
      expect(mobileCard).toBeInTheDocument();
    });

    it('should apply highlighted class', () => {
      const { container } = render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            isHighlighted={true}
          />
        </TestWrapper>
      );

      const mobileCard = container.querySelector('.highlighted');
      expect(mobileCard).toBeInTheDocument();
    });

    it('should apply hovered class', () => {
      const { container } = render(
        <TestWrapper>
          <TaskRowMobile
            {...defaultProps}
            isHovered={true}
          />
        </TestWrapper>
      );

      const mobileCard = container.querySelector('.hovered');
      expect(mobileCard).toBeInTheDocument();
    });
  });
});
