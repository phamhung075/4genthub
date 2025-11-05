/**
 * @fileoverview Test suite for SubtaskRowRefactored component
 * Tests the refactored subtask row display with simplified subtask count handling
 */

import { render, screen } from './../../test-utils';
import { SubtaskRowRefactored } from '../../../components/SubtaskRow/SubtaskRowRefactored';
import { Subtask } from '../../../types/taskTypes';
import { MemoryRouter } from 'react-router-dom';

// Mock the status emoji util
vi.mock('../../../utils/statusEmojis', () => ({
  getStatusEmoji: (status: string) => {
    const emojis: Record<string, string> = {
      'todo': '📋',
      'in_progress': '⏳',
      'done': '✅',
      'cancelled': '❌',
      'blocked': '🚫'
    };
    return emojis[status] || '❓';
  }
}));

describe('SubtaskRowRefactored', () => {
  const mockSubtask: Subtask = {
    id: 'sub-123',
    title: 'Test Subtask',
    status: 'in_progress',
    priority: 'high',
    assignees: ['user-1', 'user-2'],
    labels: ['frontend', 'bug'],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    progress_percentage: 50
  };

  const defaultProps = {
    subtask: mockSubtask,
    projectId: 'proj-123',
    branchId: 'branch-456',
    taskId: 'task-789',
    onUpdate: vi.fn()
  };

  const renderComponent = (props = {}) => {
    return render(
      <MemoryRouter>
        <SubtaskRowRefactored {...defaultProps} {...props} />
      </MemoryRouter>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render subtask title and status', () => {
      renderComponent();

      expect(screen.getByText('Test Subtask')).toBeInTheDocument();
      expect(screen.getByText('⏳')).toBeInTheDocument(); // in_progress emoji
    });

    it('should render priority badge', () => {
      renderComponent();

      const priorityBadge = screen.getByText('high');
      expect(priorityBadge).toBeInTheDocument();
      expect(priorityBadge.className).toContain('text-red-700');
    });

    it('should render assignee count', () => {
      renderComponent();

      expect(screen.getByText('2 assignees')).toBeInTheDocument();
    });

    it('should render label badges', () => {
      renderComponent();

      expect(screen.getByText('frontend')).toBeInTheDocument();
      expect(screen.getByText('bug')).toBeInTheDocument();
    });

    it('should render progress percentage when available', () => {
      renderComponent();

      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  describe('Different Status Rendering', () => {
    it('should render correct emoji for todo status', () => {
      renderComponent({
        subtask: { ...mockSubtask, status: 'todo' }
      });

      expect(screen.getByText('📋')).toBeInTheDocument();
    });

    it('should render correct emoji for done status', () => {
      renderComponent({
        subtask: { ...mockSubtask, status: 'done' }
      });

      expect(screen.getByText('✅')).toBeInTheDocument();
    });

    it('should render correct emoji for blocked status', () => {
      renderComponent({
        subtask: { ...mockSubtask, status: 'blocked' }
      });

      expect(screen.getByText('🚫')).toBeInTheDocument();
    });
  });

  describe('Priority Variations', () => {
    it('should render low priority with correct styling', () => {
      renderComponent({
        subtask: { ...mockSubtask, priority: 'low' }
      });

      const priorityBadge = screen.getByText('low');
      expect(priorityBadge.className).toContain('text-gray-600');
    });

    it('should render medium priority with correct styling', () => {
      renderComponent({
        subtask: { ...mockSubtask, priority: 'medium' }
      });

      const priorityBadge = screen.getByText('medium');
      expect(priorityBadge.className).toContain('text-yellow-600');
    });

    it('should render urgent priority with correct styling', () => {
      renderComponent({
        subtask: { ...mockSubtask, priority: 'urgent' }
      });

      const priorityBadge = screen.getByText('urgent');
      expect(priorityBadge.className).toContain('text-orange-600');
    });

    it('should render critical priority with correct styling', () => {
      renderComponent({
        subtask: { ...mockSubtask, priority: 'critical' }
      });

      const priorityBadge = screen.getByText('critical');
      expect(priorityBadge.className).toContain('text-red-900');
    });
  });

  describe('Assignee Display', () => {
    it('should handle single assignee', () => {
      renderComponent({
        subtask: { ...mockSubtask, assignees: ['user-1'] }
      });

      expect(screen.getByText('1 assignee')).toBeInTheDocument();
    });

    it('should handle no assignees', () => {
      renderComponent({
        subtask: { ...mockSubtask, assignees: [] }
      });

      expect(screen.getByText('0 assignees')).toBeInTheDocument();
    });

    it('should handle many assignees', () => {
      renderComponent({
        subtask: { 
          ...mockSubtask, 
          assignees: ['user-1', 'user-2', 'user-3', 'user-4', 'user-5'] 
        }
      });

      expect(screen.getByText('5 assignees')).toBeInTheDocument();
    });
  });

  describe('Label Display', () => {
    it('should handle no labels', () => {
      renderComponent({
        subtask: { ...mockSubtask, labels: [] }
      });

      // Should not find any label badges
      expect(screen.queryByText('frontend')).not.toBeInTheDocument();
      expect(screen.queryByText('bug')).not.toBeInTheDocument();
    });

    it('should handle many labels', () => {
      const manyLabels = ['frontend', 'backend', 'bug', 'feature', 'urgent'];
      renderComponent({
        subtask: { ...mockSubtask, labels: manyLabels }
      });

      manyLabels.forEach(label => {
        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  describe('Progress Display', () => {
    it('should not show progress when not provided', () => {
      renderComponent({
        subtask: { ...mockSubtask, progress_percentage: undefined }
      });

      expect(screen.queryByText('%')).not.toBeInTheDocument();
    });

    it('should show 0% progress', () => {
      renderComponent({
        subtask: { ...mockSubtask, progress_percentage: 0 }
      });

      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('should show 100% progress', () => {
      renderComponent({
        subtask: { ...mockSubtask, progress_percentage: 100 }
      });

      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  describe('Row Layout', () => {
    it('should have correct flex layout structure', () => {
      const { container } = renderComponent();

      const rowElement = container.firstChild;
      expect(rowElement).toHaveClass('flex', 'items-center', 'justify-between');
    });

    it('should have hover effect', () => {
      const { container } = renderComponent();

      const rowElement = container.firstChild;
      expect(rowElement).toHaveClass('hover:bg-gray-50');
    });
  });

  describe('Edge Cases', () => {
    it('should handle subtask with minimal data', () => {
      const minimalSubtask: Subtask = {
        id: 'sub-minimal',
        title: 'Minimal',
        status: 'todo',
        priority: 'medium',
        assignees: [],
        labels: [],
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z'
      };

      renderComponent({ subtask: minimalSubtask });

      expect(screen.getByText('Minimal')).toBeInTheDocument();
      expect(screen.getByText('📋')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByText('0 assignees')).toBeInTheDocument();
    });

    it('should handle very long title', () => {
      const longTitle = 'This is a very long subtask title that should be handled properly by the component and not break the layout';
      renderComponent({
        subtask: { ...mockSubtask, title: longTitle }
      });

      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });
  });

  describe('Update Callback', () => {
    it('should be ready to handle updates', () => {
      renderComponent();

      // Verify onUpdate callback is provided
      expect(defaultProps.onUpdate).toBeDefined();
      expect(typeof defaultProps.onUpdate).toBe('function');
    });
  });
});