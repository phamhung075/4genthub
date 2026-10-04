import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TaskRowDesktop } from '../../../../components/TaskRow/components/TaskRowDesktop';
import type { TaskRowDesktopProps, TaskSummary } from '../../../../types/taskTypes';

// Child components are mocked so the tests cover only what TaskRowDesktop decides:
// which data reaches each child, what the row shows and which callbacks it fires.
vi.mock('../../../../components/TaskRow/components/TaskCopyButtons', () => ({
  TaskCopyButtons: ({ taskId, taskName }: any) => (
    <span data-testid="copy-buttons" data-task-id={taskId} data-task-name={taskName} />
  )
}));

vi.mock('../../../../components/TaskRow/components/TaskRowActions', () => ({
  TaskRowActions: ({ taskId, projectId, taskTreeId, variant }: any) => (
    <span
      data-testid="row-actions"
      data-task-id={taskId}
      data-project-id={projectId}
      data-tree-id={taskTreeId}
      data-variant={variant}
    />
  )
}));

vi.mock('../../../../components/ui/ProgressDisplay', () => ({
  ProgressDisplayEnhanced: ({ status, progressPercentage }: any) => (
    <span data-testid="progress" data-status={status} data-percentage={progressPercentage} />
  )
}));

vi.mock('../../../../components/ui/holographic-badges', () => ({
  HolographicStatusBadge: ({ status }: any) => <span data-testid="status-badge">{status}</span>,
  HolographicPriorityBadge: ({ priority }: any) => <span data-testid="priority-badge">{priority}</span>
}));

vi.mock('../../../../components/ClickableAssignees', () => ({
  default: ({ assignees, onAgentClick, task }: any) => (
    <button data-testid="assignees" onClick={() => onAgentClick(assignees[0], task)}>
      {assignees.join(',')}
    </button>
  )
}));

vi.mock('../../../../components/LazySubtaskList', () => ({
  default: ({ projectId, taskTreeId, parentTaskId }: any) => (
    <div
      data-testid="subtask-list"
      data-project-id={projectId}
      data-tree-id={taskTreeId}
      data-parent-id={parentTaskId}
    />
  )
}));

const summary: TaskSummary = {
  id: 'task-1',
  title: 'Test Task',
  status: 'todo',
  priority: 'medium',
  assignees: ['coding-agent', 'debugger-agent'],
  has_dependencies: false,
  has_context: false,
  subtask_count: 2,
  dependency_count: 0
};

const buildProps = (overrides: Partial<TaskRowDesktopProps> = {}): TaskRowDesktopProps => ({
  summary,
  fullTask: null,
  isHighlighted: false,
  isHovered: false,
  isExpanded: false,
  isLoading: false,
  projectId: 'project-1',
  taskTreeId: 'branch-1',
  onToggleExpansion: vi.fn(),
  onOpenDialog: vi.fn(),
  onHover: vi.fn(),
  elementRef: React.createRef<HTMLTableRowElement>(),
  ...overrides
});

const renderRow = (overrides: Partial<TaskRowDesktopProps> = {}) => {
  const props = buildProps(overrides);
  const view = render(
    <table>
      <tbody>
        <TaskRowDesktop {...props} />
      </tbody>
    </table>
  );
  return { props, ...view };
};

describe('TaskRowDesktop', () => {
  beforeEach(() => {
    // The expand handler logs; keep the test output quiet.
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('content', () => {
    it('shows the title, status and priority of the summary', () => {
      renderRow();

      expect(screen.getByText('Test Task')).toBeInTheDocument();
      expect(screen.getByTestId('status-badge')).toHaveTextContent('todo');
      expect(screen.getByTestId('priority-badge')).toHaveTextContent('medium');
    });

    it('passes the task identity to the copy buttons and the project ids to the actions', () => {
      renderRow();

      expect(screen.getByTestId('copy-buttons')).toHaveAttribute('data-task-id', 'task-1');
      expect(screen.getByTestId('copy-buttons')).toHaveAttribute('data-task-name', 'Test Task');
      const actions = screen.getByTestId('row-actions');
      expect(actions).toHaveAttribute('data-task-id', 'task-1');
      expect(actions).toHaveAttribute('data-project-id', 'project-1');
      expect(actions).toHaveAttribute('data-tree-id', 'branch-1');
      expect(actions).toHaveAttribute('data-variant', 'desktop');
    });

    it('prefers the full task status for the progress display', () => {
      renderRow({ fullTask: { status: 'in_progress', progress_percentage: 40 } });

      const progress = screen.getByTestId('progress');
      expect(progress).toHaveAttribute('data-status', 'in_progress');
      expect(progress).toHaveAttribute('data-percentage', '40');
    });

    it('uses the summary status for the progress display without a full task', () => {
      renderRow();

      expect(screen.getByTestId('progress')).toHaveAttribute('data-status', 'todo');
    });
  });

  describe('subtask count badge', () => {
    it('shows subtask_count from the summary', () => {
      renderRow();

      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('falls back to the subtasks of the full task', () => {
      renderRow({
        summary: { ...summary, subtask_count: undefined },
        fullTask: { subtasks: ['a', 'b', 'c'] }
      });

      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('shows no badge when there are no subtasks', () => {
      renderRow({ summary: { ...summary, subtask_count: 0 } });

      expect(screen.queryByText('0')).not.toBeInTheDocument();
    });
  });

  describe('dependencies', () => {
    it('shows None when the task has no dependencies', () => {
      renderRow();

      expect(screen.getByText('None')).toBeInTheDocument();
    });

    it('pluralizes the dependency count', () => {
      renderRow({ summary: { ...summary, has_dependencies: true, dependency_count: 3 } });

      expect(screen.getByText('3 dependencies')).toBeInTheDocument();
    });

    it('uses the singular for one dependency', () => {
      renderRow({ summary: { ...summary, has_dependencies: true, dependency_count: 1 } });

      const badge = screen.getByText('1 dependency');
      expect(badge).toHaveAttribute('title', 'This task depends on 1 other task.');
    });

    it('falls back to the dependencies of the full task', () => {
      renderRow({
        summary: { ...summary, has_dependencies: true, dependency_count: undefined },
        fullTask: { dependencies: ['d1', 'd2'] }
      });

      expect(screen.getByText('2 dependencies')).toBeInTheDocument();
    });
  });

  describe('assignees', () => {
    it('shows Unassigned without assignees', () => {
      renderRow({ summary: { ...summary, assignees: [] } });

      expect(screen.getByText('Unassigned')).toBeInTheDocument();
      expect(screen.queryByTestId('assignees')).not.toBeInTheDocument();
    });

    it('opens the agent-info dialog with the agent name and the task title', () => {
      const { props } = renderRow();

      fireEvent.click(screen.getByTestId('assignees'));

      expect(props.onOpenDialog).toHaveBeenCalledWith('agent-info', undefined, {
        agentName: 'coding-agent',
        taskTitle: 'Test Task'
      });
    });

    it('passes the full task to the assignees when it is loaded', () => {
      const { props } = renderRow({ fullTask: { title: 'Full Task Title' } });

      fireEvent.click(screen.getByTestId('assignees'));

      expect(props.onOpenDialog).toHaveBeenCalledWith('agent-info', undefined, {
        agentName: 'coding-agent',
        taskTitle: 'Full Task Title'
      });
    });
  });

  describe('expansion', () => {
    it('calls onToggleExpansion when the expand button is clicked', () => {
      const { props } = renderRow();

      fireEvent.click(screen.getAllByRole('button')[0]);

      expect(props.onToggleExpansion).toHaveBeenCalledTimes(1);
    });

    it('does not let the click reach the row', () => {
      const rowClick = vi.fn();
      const props = buildProps();
      render(
        <table>
          <tbody onClick={rowClick}>
            <TaskRowDesktop {...props} />
          </tbody>
        </table>
      );

      fireEvent.click(screen.getAllByRole('button')[0]);

      expect(props.onToggleExpansion).toHaveBeenCalledTimes(1);
      expect(rowClick).not.toHaveBeenCalled();
    });

    it('disables the expand button and shows a spinner while loading', () => {
      const { container } = renderRow({ isLoading: true });

      expect(screen.getAllByRole('button')[0]).toBeDisabled();
      expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('does not show the subtask list while collapsed', () => {
      renderRow({ fullTask: { id: 'task-1' } });

      expect(screen.queryByTestId('subtask-list')).not.toBeInTheDocument();
    });

    it('shows the subtask list for the task when expanded with a full task', () => {
      renderRow({ isExpanded: true, fullTask: { id: 'task-1' } });

      const list = screen.getByTestId('subtask-list');
      expect(list).toHaveAttribute('data-project-id', 'project-1');
      expect(list).toHaveAttribute('data-tree-id', 'branch-1');
      expect(list).toHaveAttribute('data-parent-id', 'task-1');
    });

    it('waits for the full task before showing the subtask list', () => {
      renderRow({ isExpanded: true, fullTask: null });

      expect(screen.queryByTestId('subtask-list')).not.toBeInTheDocument();
    });
  });

  describe('row', () => {
    it('reports hover enter with the task id and leave with null', () => {
      const { props, container } = renderRow();
      const row = container.querySelector('tr') as HTMLTableRowElement;

      fireEvent.mouseEnter(row);
      fireEvent.mouseLeave(row);

      expect(props.onHover).toHaveBeenNthCalledWith(1, 'task-1');
      expect(props.onHover).toHaveBeenNthCalledWith(2, null);
    });

    it('attaches elementRef to the row', () => {
      const { props, container } = renderRow();

      expect(props.elementRef.current).toBe(container.querySelector('tr'));
    });

    it('applies highlight, hover, animation and loading classes', () => {
      const { container, rerender, props } = renderRow({
        isHighlighted: true,
        animationClass: 'fade-in',
        isLoading: true
      });
      const row = () => container.querySelector('tr') as HTMLTableRowElement;

      expect(row()).toHaveClass('cursor-pointer', 'bg-orange-100', 'fade-in', 'loading');

      rerender(
        <table>
          <tbody>
            <TaskRowDesktop {...props} isHighlighted={false} isHovered={true} isLoading={false} animationClass="" />
          </tbody>
        </table>
      );

      expect(row()).toHaveClass('bg-violet-200');
      expect(row()).not.toHaveClass('loading', 'bg-orange-100');
    });
  });
});
