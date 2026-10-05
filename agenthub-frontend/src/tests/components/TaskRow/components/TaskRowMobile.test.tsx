/**
 * @fileoverview Test suite for TaskRowMobile component
 *
 * The component takes `TaskRowMobileProps` (`summary`, `fullTask`, expansion/hover
 * state and callbacks) - not a single `task` prop. It composes the holographic
 * badges, ProgressDisplayEnhanced, ClickableAssignees, the copy buttons,
 * TaskRowActions and (when expanded with a full task) LazySubtaskList.
 *
 * The child presentational components are stubbed so the assertions describe the
 * contract TaskRowMobile provides to them plus its own layout and interactions.
 */

import { render, screen, fireEvent } from './../../../test-utils';
import React from 'react';
import { TaskRowMobile } from '../../../../components/TaskRow/components/TaskRowMobile';
import type { TaskSummary } from '../../../../types/taskTypes';

vi.mock('../../../../components/ui/holographic-badges', () => ({
  HolographicStatusBadge: ({ status, size }: any) => (
    <span data-testid="status-badge" data-status={status} data-size={size} />
  ),
  HolographicPriorityBadge: ({ priority, size }: any) => (
    <span data-testid="priority-badge" data-priority={priority} data-size={size} />
  )
}));

vi.mock('../../../../components/ui/ProgressDisplay', () => ({
  ProgressDisplayEnhanced: ({ status, progressPercentage }: any) => (
    <div
      data-testid="progress-display"
      data-status={status}
      data-progress={progressPercentage ?? 'none'}
    />
  )
}));

vi.mock('../../../../components/TaskRow/components/TaskCopyButtons', () => ({
  TaskCopyButtons: ({ taskId, taskName }: any) => (
    <div data-testid="task-copy-buttons" data-task-id={taskId} data-task-name={taskName} />
  )
}));

vi.mock('../../../../components/TaskRow/components/TaskRowActions', () => ({
  TaskRowActions: ({ taskId, projectId, taskTreeId, onOpenDialog, variant }: any) => (
    <div
      data-testid="task-row-actions"
      data-task-id={taskId}
      data-project-id={projectId}
      data-task-tree-id={taskTreeId}
      data-variant={variant}
    >
      <button onClick={() => onOpenDialog('details', taskId)}>Open details</button>
    </div>
  )
}));

vi.mock('../../../../components/ClickableAssignees', () => ({
  default: ({ assignees, task, variant }: { assignees: string[]; task?: { title?: string }; variant?: string }) => (
    <div
      data-testid="clickable-assignees"
      data-assignees={assignees.join(',')}
      data-task-title={task?.title}
      data-variant={variant}
    >
      {assignees.map((assignee: string) => (
        <span key={assignee}>{`agent-${assignee}`}</span>
      ))}
    </div>
  )
}));

vi.mock('../../../../components/LazySubtaskList', () => ({
  default: ({ projectId, taskTreeId, parentTaskId }: any) => (
    <div
      data-testid="lazy-subtask-list"
      data-project-id={projectId}
      data-task-tree-id={taskTreeId}
      data-parent-task-id={parentTaskId}
    />
  )
}));

describe('TaskRowMobile', () => {
  const mockSummary: TaskSummary = {
    id: 'task-123',
    title: 'Mobile Task Title',
    status: 'in_progress',
    priority: 'high',
    assignees: ['user-1', 'user-2'],
    has_dependencies: false,
    has_context: false,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    subtask_count: 0
  };

  const defaultProps = {
    summary: mockSummary,
    fullTask: null as any,
    isHighlighted: false,
    isHovered: false,
    isExpanded: false,
    isLoading: false,
    projectId: 'proj-123',
    taskTreeId: 'tree-456',
    onToggleExpansion: vi.fn(),
    onOpenDialog: vi.fn(),
    onHover: vi.fn(),
    elementRef: React.createRef<HTMLDivElement>(),
    animationClass: ''
  };

  const renderComponent = (props: Partial<typeof defaultProps> = {}) =>
    render(<TaskRowMobile {...defaultProps} {...props} />);

  const getExpandButton = (container: HTMLElement) =>
    container.querySelector('button.flex-shrink-0') as HTMLButtonElement;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Mobile Layout', () => {
    it('should render with mobile-optimized layout', () => {
      const { container } = renderComponent();

      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toHaveClass('rounded-lg', 'mb-3', 'cursor-pointer');
    });

    it('should render the inner card container', () => {
      const { container } = renderComponent();

      const card = container.querySelector('.bg-surface');
      expect(card).toHaveClass('rounded-lg', 'shadow-sm', 'border');
    });

    it('should display the title prominently', () => {
      renderComponent();

      const title = screen.getByText('Mobile Task Title');
      expect(title.tagName).toBe('H3');
      expect(title.className).toContain('font-medium');
    });

    it('should pass the task id and title to the copy buttons', () => {
      renderComponent();

      const copyButtons = screen.getByTestId('task-copy-buttons');
      expect(copyButtons).toHaveAttribute('data-task-id', 'task-123');
      expect(copyButtons).toHaveAttribute('data-task-name', 'Mobile Task Title');
    });

    it('should render the status and priority badges', () => {
      renderComponent();

      expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'in_progress');
      expect(screen.getByTestId('priority-badge')).toHaveAttribute('data-priority', 'high');
    });
  });

  describe('Status Variations', () => {
    const statuses = ['todo', 'done', 'blocked', 'review', 'testing', 'cancelled'];

    statuses.forEach(status => {
      it(`should pass the ${status} status to the status badge`, () => {
        renderComponent({ summary: { ...mockSummary, status } });

        expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', status);
      });
    });
  });

  describe('Priority Display', () => {
    const priorities = ['low', 'medium', 'high', 'urgent', 'critical'];

    priorities.forEach(priority => {
      it(`should pass the ${priority} priority to the priority badge`, () => {
        renderComponent({ summary: { ...mockSummary, priority } });

        expect(screen.getByTestId('priority-badge')).toHaveAttribute('data-priority', priority);
      });
    });
  });

  describe('Progress Display', () => {
    it('should fall back to the summary status when there is no full task', () => {
      renderComponent();

      const progress = screen.getByTestId('progress-display');
      expect(progress).toHaveAttribute('data-status', 'in_progress');
      expect(progress).toHaveAttribute('data-progress', 'none');
    });

    it('should prefer the full task status and progress when available', () => {
      renderComponent({
        fullTask: {
          id: 'task-123',
          title: 'Mobile Task Title',
          status: 'done',
          progress_percentage: 75
        }
      });

      const progress = screen.getByTestId('progress-display');
      expect(progress).toHaveAttribute('data-status', 'done');
      expect(progress).toHaveAttribute('data-progress', '75');
    });
  });

  describe('Mobile Metadata', () => {
    it('should display the subtask count from the summary', () => {
      renderComponent({ summary: { ...mockSummary, subtask_count: 2 } });

      expect(screen.getByText('2 subtasks')).toBeInTheDocument();
    });

    it('should not show a subtask badge when there are no subtasks', () => {
      renderComponent({ summary: { ...mockSummary, subtask_count: 0 } });

      expect(screen.queryByText(/subtasks/)).not.toBeInTheDocument();
    });

    it('should fall back to the full task subtasks length for the count', () => {
      renderComponent({
        summary: { ...mockSummary, subtask_count: undefined },
        fullTask: { subtasks: [{ id: 'sub-1' }, { id: 'sub-2' }, { id: 'sub-3' }] }
      });

      expect(screen.getByText('3 subtasks')).toBeInTheDocument();
    });

    it('should display a dependency badge when the task has dependencies', () => {
      renderComponent({
        summary: { ...mockSummary, has_dependencies: true, dependency_count: 3 }
      });

      expect(screen.getByText('3 deps')).toBeInTheDocument();
    });

    it('should use the singular label for a single dependency', () => {
      renderComponent({
        summary: { ...mockSummary, has_dependencies: true, dependency_count: 1 }
      });

      expect(screen.getByText('1 dep')).toBeInTheDocument();
    });

    it('should not show a dependency badge when the task has no dependencies', () => {
      renderComponent({ summary: { ...mockSummary, has_dependencies: false } });

      expect(screen.queryByText(/ deps?$/)).not.toBeInTheDocument();
    });

    it('should pass the assignees and task to ClickableAssignees', () => {
      renderComponent();

      const assignees = screen.getByTestId('clickable-assignees');
      expect(assignees).toHaveAttribute('data-assignees', 'user-1,user-2');
      expect(assignees).toHaveAttribute('data-task-title', 'Mobile Task Title');
      expect(assignees).toHaveAttribute('data-variant', 'secondary');
    });

    it('should not render ClickableAssignees when there are no assignees', () => {
      renderComponent({ summary: { ...mockSummary, assignees: [] } });

      expect(screen.queryByTestId('clickable-assignees')).not.toBeInTheDocument();
    });
  });

  describe('Mobile Actions', () => {
    it('should render the expand button', () => {
      const { container } = renderComponent();

      expect(getExpandButton(container)).toBeInTheDocument();
    });

    it('should call onToggleExpansion when the expand button is clicked', () => {
      const { container } = renderComponent();

      fireEvent.click(getExpandButton(container));

      expect(defaultProps.onToggleExpansion).toHaveBeenCalledTimes(1);
    });

    it('should disable the expand button while loading', () => {
      const { container } = renderComponent({ isLoading: true });

      expect(getExpandButton(container)).toBeDisabled();
    });

    it('should pass task, project and tree identifiers to TaskRowActions', () => {
      renderComponent();

      const actions = screen.getByTestId('task-row-actions');
      expect(actions).toHaveAttribute('data-task-id', 'task-123');
      expect(actions).toHaveAttribute('data-project-id', 'proj-123');
      expect(actions).toHaveAttribute('data-task-tree-id', 'tree-456');
      expect(actions).toHaveAttribute('data-variant', 'mobile');
    });

    it('should forward dialog actions from TaskRowActions', () => {
      renderComponent();

      fireEvent.click(screen.getByText('Open details'));

      expect(defaultProps.onOpenDialog).toHaveBeenCalledWith('details', 'task-123');
    });
  });

  describe('Expansion', () => {
    it('should not render LazySubtaskList when collapsed', () => {
      renderComponent({ isExpanded: false, fullTask: { id: 'task-123' } });

      expect(screen.queryByTestId('lazy-subtask-list')).not.toBeInTheDocument();
    });

    it('should not render LazySubtaskList when expanded without a full task', () => {
      renderComponent({ isExpanded: true, fullTask: null });

      expect(screen.queryByTestId('lazy-subtask-list')).not.toBeInTheDocument();
    });

    it('should render LazySubtaskList with the parent id when expanded with a full task', () => {
      renderComponent({ isExpanded: true, fullTask: { id: 'task-123' } });

      const list = screen.getByTestId('lazy-subtask-list');
      expect(list).toHaveAttribute('data-project-id', 'proj-123');
      expect(list).toHaveAttribute('data-task-tree-id', 'tree-456');
      expect(list).toHaveAttribute('data-parent-task-id', 'task-123');
    });
  });

  describe('Interaction State', () => {
    it('should call onHover with the task id on mouse enter', () => {
      const { container } = renderComponent();

      fireEvent.mouseEnter(container.firstChild as HTMLElement);

      expect(defaultProps.onHover).toHaveBeenCalledWith('task-123');
    });

    it('should call onHover with null on mouse leave', () => {
      const { container } = renderComponent();

      fireEvent.mouseLeave(container.firstChild as HTMLElement);

      expect(defaultProps.onHover).toHaveBeenCalledWith(null);
    });

    it('should apply the highlighted border classes', () => {
      const { container } = renderComponent({ isHighlighted: true });

      expect(container.firstChild).toHaveClass('border-blue-400');
    });

    it('should apply the hovered border classes', () => {
      const { container } = renderComponent({ isHovered: true });

      expect(container.firstChild).toHaveClass('border-violet-400');
    });

    it('should apply the default border classes', () => {
      const { container } = renderComponent();

      expect(container.firstChild).toHaveClass('border-surface-border');
    });

    it('should apply the animation class on the container', () => {
      const { container } = renderComponent({ animationClass: 'animate-fade-in' });

      expect(container.firstChild).toHaveClass('animate-fade-in');
    });

    it('should apply the loading class on the container while loading', () => {
      const { container } = renderComponent({ isLoading: true });

      expect(container.firstChild).toHaveClass('loading');
    });
  });

  describe('Edge Cases', () => {
    it('should handle a task with minimal data', () => {
      const minimalTask: TaskSummary = {
        id: 'task-min',
        title: 'Minimal Task',
        status: 'todo',
        priority: 'medium',
        assignees: [],
        has_dependencies: false,
        has_context: false,
        subtask_count: 0
      };

      renderComponent({ summary: minimalTask });

      expect(screen.getByText('Minimal Task')).toBeInTheDocument();
      expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'todo');
      expect(screen.queryByTestId('clickable-assignees')).not.toBeInTheDocument();
    });

    it('should handle a very long title', () => {
      const longTitle =
        'This is an extremely long task title that should be properly handled on mobile devices without breaking the layout';

      renderComponent({ summary: { ...mockSummary, title: longTitle } });

      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should pass all provided labels through to ClickableAssignees', () => {
      // TaskRowMobile does not render labels itself; it surfaces each assignee.
      renderComponent({
        summary: { ...mockSummary, assignees: ['label1', 'label2', 'label3', 'label4', 'label5'] }
      });

      expect(screen.getByTestId('clickable-assignees')).toHaveAttribute(
        'data-assignees',
        'label1,label2,label3,label4,label5'
      );
    });
  });
});
