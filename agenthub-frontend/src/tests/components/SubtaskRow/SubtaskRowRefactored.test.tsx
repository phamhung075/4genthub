/**
 * @fileoverview Test suite for SubtaskRowRefactored component
 *
 * The component exposes a default export and takes the current `SubtaskRowProps`
 * shape (`summary`, `parentTaskId`, action callbacks). It renders the status and
 * priority via SubtaskRowBadges, the assignees via SubtaskRowAssignees (count is
 * derived from `summary.assignees?.length`) and the action buttons via
 * SubtaskRowActions.
 */

import { render, screen, fireEvent } from './../../test-utils';
import SubtaskRowRefactored from '../../../components/SubtaskRow/SubtaskRowRefactored';
import type { SubtaskSummary } from '../../../types/taskTypes';

// ParentTaskReference performs its own data fetch; stub it so the row test stays isolated.
vi.mock('../../../components/ui/ParentTaskReference', () => ({
  ParentTaskReference: ({ parentTaskId }: any) => (
    <div data-testid="parent-task-ref">Parent: {parentTaskId}</div>
  )
}));

// The animation hook talks to AnimationFactory and timers; stub it to a visible, non-animated row.
vi.mock('../../../components/SubtaskRow/hooks/useSubtaskAnimation', () => ({
  useSubtaskAnimation: () => ({
    animationState: 'none',
    isVisible: true,
    animationClass: '',
    elementRef: { current: null }
  })
}));

describe('SubtaskRowRefactored', () => {
  const mockSummary: SubtaskSummary = {
    id: 'sub-123',
    title: 'Test Subtask',
    status: 'in_progress',
    priority: 'high',
    assignees: ['user-1', 'user-2'],
    progress_percentage: 50
  };

  const defaultProps = {
    summary: mockSummary,
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

  const renderRow = (props: Partial<typeof defaultProps> = {}) =>
    render(
      <table>
        <tbody>
          <SubtaskRowRefactored {...defaultProps} {...props} />
        </tbody>
      </table>
    );

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render subtask title', () => {
      renderRow();

      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
    });

    it('should render the status badge for in_progress', () => {
      renderRow();

      expect(screen.getByText('In Progress')).toBeInTheDocument();
    });

    it('should render the priority badge for high', () => {
      renderRow();

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('should render the abbreviated copyable id with the S label', () => {
      renderRow();

      expect(screen.getByText('S sub-123')).toBeInTheDocument();
    });

    it('should render the parent task reference', () => {
      renderRow();

      expect(screen.getByTestId('parent-task-ref')).toHaveTextContent('Parent: parent-task-456');
    });

    it('should render progress percentage when available', () => {
      renderRow();

      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  describe('Status Rendering', () => {
    const statuses: Array<[string, string]> = [
      ['todo', 'To Do'],
      ['in_progress', 'In Progress'],
      ['done', 'Done'],
      ['blocked', 'Blocked'],
      ['review', 'Review'],
      ['testing', 'Testing'],
      ['cancelled', 'Cancelled']
    ];

    statuses.forEach(([status, label]) => {
      it(`should render the ${status} status badge`, () => {
        renderRow({ summary: { ...mockSummary, status } });

        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  describe('Priority Variations', () => {
    const priorities: Array<[string, string]> = [
      ['low', 'Low'],
      ['medium', 'Medium'],
      ['high', 'High'],
      ['urgent', 'Urgent'],
      ['critical', 'Critical']
    ];

    priorities.forEach(([priority, label]) => {
      it(`should render the ${priority} priority badge`, () => {
        renderRow({ summary: { ...mockSummary, priority } });

        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  describe('Assignee Display', () => {
    it('should render both badges for two assignees', () => {
      renderRow();

      expect(screen.getByText('user-1')).toBeInTheDocument();
      expect(screen.getByText('user-2')).toBeInTheDocument();
      expect(screen.queryByText(/^\+\d+$/)).not.toBeInTheDocument();
    });

    it('should handle a single assignee', () => {
      renderRow({ summary: { ...mockSummary, assignees: ['user-1'] } });

      expect(screen.getByText('user-1')).toBeInTheDocument();
    });

    it('should show "No assignees" when the assignees array is empty', () => {
      renderRow({ summary: { ...mockSummary, assignees: [] } });

      expect(screen.getByText('No assignees')).toBeInTheDocument();
    });

    it('should show "No assignees" when assignees is undefined', () => {
      renderRow({ summary: { ...mockSummary, assignees: undefined } });

      expect(screen.getByText('No assignees')).toBeInTheDocument();
    });

    it('should cap visible assignees at two and show the overflow count', () => {
      renderRow({
        summary: {
          ...mockSummary,
          assignees: ['user-1', 'user-2', 'user-3', 'user-4', 'user-5']
        }
      });

      expect(screen.getByText('user-1')).toBeInTheDocument();
      expect(screen.getByText('user-2')).toBeInTheDocument();
      expect(screen.queryByText('user-3')).not.toBeInTheDocument();
      expect(screen.getByText('+3')).toBeInTheDocument();
    });

    it('should call onAgentInfoClick with the assignee name', () => {
      renderRow();

      fireEvent.click(screen.getByText('user-1'));

      expect(defaultProps.onAgentInfoClick).toHaveBeenCalledWith('user-1');
    });
  });

  describe('Progress Display', () => {
    it('should not render a progress badge when progress is undefined', () => {
      renderRow({ summary: { ...mockSummary, progress_percentage: undefined } });

      expect(screen.queryByText('%')).not.toBeInTheDocument();
    });

    it('should not render a progress badge for 0%', () => {
      renderRow({ summary: { ...mockSummary, progress_percentage: 0 } });

      expect(screen.queryByText('0%')).not.toBeInTheDocument();
    });

    it('should render 100% progress', () => {
      renderRow({ summary: { ...mockSummary, progress_percentage: 100 } });

      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  describe('Action Callbacks', () => {
    it('should dispatch details action', () => {
      renderRow();

      fireEvent.click(screen.getByTitle('View details'));

      expect(defaultProps.onSubtaskAction).toHaveBeenCalledWith('details', 'sub-123');
    });

    it('should dispatch edit action', () => {
      renderRow();

      fireEvent.click(screen.getByTitle('Edit subtask'));

      expect(defaultProps.onSubtaskAction).toHaveBeenCalledWith('edit', 'sub-123');
    });

    it('should dispatch complete action', () => {
      renderRow();

      fireEvent.click(screen.getByTitle('Complete subtask'));

      expect(defaultProps.onSubtaskAction).toHaveBeenCalledWith('complete', 'sub-123');
    });

    it('should dispatch delete action', () => {
      renderRow();

      fireEvent.click(screen.getByTitle('Delete subtask'));

      expect(defaultProps.onDeleteSubtask).toHaveBeenCalledWith('sub-123');
    });
  });

  describe('Loading State', () => {
    it('should add the loading class to the row when isLoading is true', () => {
      const { container } = renderRow({ isLoading: true });

      expect(container.querySelector('tr')).toHaveClass('loading');
    });

    it('should not add the loading class when isLoading is false', () => {
      const { container } = renderRow({ isLoading: false });

      expect(container.querySelector('tr')).not.toHaveClass('loading');
    });
  });

  describe('Edge Cases', () => {
    it('should handle subtask with minimal data', () => {
      const minimalSubtask: SubtaskSummary = {
        id: 'sub-minimal',
        title: 'Minimal',
        status: 'todo',
        priority: 'medium',
        assignees: [],
        progress_percentage: undefined
      };

      renderRow({ summary: minimalSubtask });

      expect(screen.getByText('Minimal')).toBeInTheDocument();
      expect(screen.getByText('To Do')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('No assignees')).toBeInTheDocument();
    });

    it('should handle a very long title', () => {
      const longTitle =
        'This is a very long subtask title that should be handled properly by the component and not break the layout';

      renderRow({ summary: { ...mockSummary, title: longTitle } });

      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });
  });
});
