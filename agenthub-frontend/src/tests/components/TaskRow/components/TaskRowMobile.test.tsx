/**
 * @fileoverview Test suite for TaskRowMobile component
 * Tests mobile-specific task row rendering and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { TaskRowMobile } from '../../../../components/TaskRow/components/TaskRowMobile';
import { Task } from '../../../../types/taskTypes';
import { MemoryRouter } from 'react-router-dom';

// Mock the status emoji util
jest.mock('../../../../utils/statusEmojis', () => ({
  getStatusEmoji: (status: string) => {
    const emojis: Record<string, string> = {
      'todo': '📋',
      'in_progress': '⏳',
      'done': '✅',
      'cancelled': '❌',
      'blocked': '🚫',
      'review': '👀',
      'testing': '🧪'
    };
    return emojis[status] || '❓';
  }
}));

describe('TaskRowMobile', () => {
  const mockTask: Task = {
    id: 'task-123',
    title: 'Mobile Task Title',
    description: 'This is a test task for mobile view',
    status: 'in_progress',
    priority: 'high',
    assignees: ['user-1', 'user-2'],
    labels: ['mobile', 'urgent'],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    details: 'Additional task details',
    estimated_effort: '2 hours',
    progress_percentage: 75,
    subtasks: []
  };

  const defaultProps = {
    task: mockTask,
    projectId: 'proj-123',
    branchId: 'branch-456',
    onDelete: jest.fn(),
    onUpdate: jest.fn()
  };

  const renderComponent = (props = {}) => {
    return render(
      <MemoryRouter>
        <TaskRowMobile {...defaultProps} {...props} />
      </MemoryRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Mobile Layout', () => {
    it('should render with mobile-optimized layout', () => {
      const { container } = renderComponent();
      
      // Check for stacked layout
      const mainContainer = container.querySelector('.bg-white');
      expect(mainContainer).toHaveClass('p-4', 'rounded-lg', 'shadow-sm');
    });

    it('should display title prominently', () => {
      renderComponent();
      
      const title = screen.getByText('Mobile Task Title');
      expect(title).toBeInTheDocument();
      expect(title.className).toContain('font-medium');
    });

    it('should show status emoji and text', () => {
      renderComponent();
      
      expect(screen.getByText('⏳')).toBeInTheDocument();
      expect(screen.getByText('in_progress')).toBeInTheDocument();
    });
  });

  describe('Priority Display', () => {
    it('should show high priority with correct mobile styling', () => {
      renderComponent();
      
      const priority = screen.getByText('HIGH');
      expect(priority).toBeInTheDocument();
      expect(priority.className).toContain('text-xs');
      expect(priority.className).toContain('bg-red-100');
    });

    it('should show medium priority correctly', () => {
      renderComponent({
        task: { ...mockTask, priority: 'medium' }
      });
      
      const priority = screen.getByText('MEDIUM');
      expect(priority.className).toContain('bg-yellow-100');
    });

    it('should show low priority correctly', () => {
      renderComponent({
        task: { ...mockTask, priority: 'low' }
      });
      
      const priority = screen.getByText('LOW');
      expect(priority.className).toContain('bg-gray-100');
    });
  });

  describe('Progress Bar', () => {
    it('should show progress bar with percentage', () => {
      renderComponent();
      
      expect(screen.getByText('75%')).toBeInTheDocument();
      
      // Check progress bar fill
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar.getAttribute('aria-valuenow')).toBe('75');
    });

    it('should not show progress bar when percentage is not provided', () => {
      renderComponent({
        task: { ...mockTask, progress_percentage: undefined }
      });
      
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    it('should handle 0% progress', () => {
      renderComponent({
        task: { ...mockTask, progress_percentage: 0 }
      });
      
      expect(screen.getByText('0%')).toBeInTheDocument();
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar.getAttribute('aria-valuenow')).toBe('0');
    });

    it('should handle 100% progress', () => {
      renderComponent({
        task: { ...mockTask, progress_percentage: 100 }
      });
      
      expect(screen.getByText('100%')).toBeInTheDocument();
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar.getAttribute('aria-valuenow')).toBe('100');
    });
  });

  describe('Mobile Metadata', () => {
    it('should display assignee count in mobile format', () => {
      renderComponent();
      
      expect(screen.getByText('👥 2')).toBeInTheDocument();
    });

    it('should display estimated effort', () => {
      renderComponent();
      
      expect(screen.getByText('⏱️ 2 hours')).toBeInTheDocument();
    });

    it('should display labels compactly', () => {
      renderComponent();
      
      const mobileLabel = screen.getByText('mobile');
      const urgentLabel = screen.getByText('urgent');
      
      expect(mobileLabel).toBeInTheDocument();
      expect(urgentLabel).toBeInTheDocument();
      expect(mobileLabel.className).toContain('text-xs');
    });
  });

  describe('Subtasks Display', () => {
    it('should show subtask count when subtasks exist', () => {
      const taskWithSubtasks = {
        ...mockTask,
        subtasks: [
          { id: 'sub-1', title: 'Subtask 1', status: 'done' },
          { id: 'sub-2', title: 'Subtask 2', status: 'in_progress' }
        ]
      };
      
      renderComponent({ task: taskWithSubtasks });
      
      expect(screen.getByText('📝 2 subtasks')).toBeInTheDocument();
    });

    it('should not show subtask count when no subtasks', () => {
      renderComponent();
      
      expect(screen.queryByText(/subtasks/)).not.toBeInTheDocument();
    });
  });

  describe('Mobile Actions', () => {
    it('should have action buttons at bottom', () => {
      renderComponent();
      
      const editButton = screen.getByRole('button', { name: /edit/i });
      const deleteButton = screen.getByRole('button', { name: /delete/i });
      
      expect(editButton).toBeInTheDocument();
      expect(deleteButton).toBeInTheDocument();
    });

    it('should handle delete action', () => {
      renderComponent();
      
      const deleteButton = screen.getByRole('button', { name: /delete/i });
      fireEvent.click(deleteButton);
      
      expect(defaultProps.onDelete).toHaveBeenCalledWith(mockTask.id);
    });

    it('should handle update action', () => {
      renderComponent();
      
      const editButton = screen.getByRole('button', { name: /edit/i });
      fireEvent.click(editButton);
      
      // In real implementation, this would open an edit modal
      // For now, verify the button exists and is clickable
      expect(editButton).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle task with minimal data', () => {
      const minimalTask: Task = {
        id: 'task-min',
        title: 'Minimal Task',
        status: 'todo',
        priority: 'medium',
        assignees: [],
        labels: [],
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        subtasks: []
      };
      
      renderComponent({ task: minimalTask });
      
      expect(screen.getByText('Minimal Task')).toBeInTheDocument();
      expect(screen.getByText('📋')).toBeInTheDocument();
      expect(screen.getByText('👥 0')).toBeInTheDocument();
    });

    it('should truncate very long title on mobile', () => {
      const longTitle = 'This is an extremely long task title that should be properly handled on mobile devices without breaking the layout';
      
      renderComponent({
        task: { ...mockTask, title: longTitle }
      });
      
      const titleElement = screen.getByText(longTitle);
      expect(titleElement).toBeInTheDocument();
      expect(titleElement.className).toContain('line-clamp-2'); // Assuming truncation CSS
    });

    it('should handle many labels gracefully', () => {
      const manyLabels = ['label1', 'label2', 'label3', 'label4', 'label5'];
      
      renderComponent({
        task: { ...mockTask, labels: manyLabels }
      });
      
      // Should show first few labels and possibly a count
      expect(screen.getByText('label1')).toBeInTheDocument();
      expect(screen.getByText('label2')).toBeInTheDocument();
      // Might show "+3 more" or similar
    });
  });

  describe('Responsive Behavior', () => {
    it('should have touch-friendly tap targets', () => {
      renderComponent();
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        // Check minimum size for touch targets
        expect(button.className).toMatch(/p-\d+/); // Has padding
      });
    });

    it('should use mobile-appropriate font sizes', () => {
      const { container } = renderComponent();
      
      const textElements = container.querySelectorAll('.text-sm, .text-xs');
      expect(textElements.length).toBeGreaterThan(0); // Uses smaller text sizes
    });
  });

  describe('Status Variations', () => {
    const statuses = ['todo', 'done', 'blocked', 'review', 'testing', 'cancelled'];
    
    statuses.forEach(status => {
      it(`should render ${status} status correctly`, () => {
        renderComponent({
          task: { ...mockTask, status }
        });
        
        expect(screen.getByText(status)).toBeInTheDocument();
      });
    });
  });
});