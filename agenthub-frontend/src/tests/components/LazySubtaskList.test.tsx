import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import LazySubtaskList from '../../components/LazySubtaskList';
import * as api from '../../api';
import Cookies from 'js-cookie';

// Mock the api module
vi.mock('../../api');

// Mock js-cookie
vi.mock('js-cookie');

// Mock lazy-loaded components
vi.mock('../../components/DeleteConfirmDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange, onConfirm, itemName }: any) => open ? (
    <div data-testid="delete-confirm-dialog">
      <div>Delete {itemName}?</div>
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={() => onOpenChange(false)}>Cancel</button>
    </div>
  ) : null
}));

vi.mock('../../components/SubtaskCompleteDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange, subtask, onComplete }: any) => open ? (
    <div data-testid="subtask-complete-dialog">
      <div>Complete {subtask?.title}?</div>
      <button onClick={() => {
        const completedSubtask = { ...subtask, status: 'done' };
        onComplete(completedSubtask);
      }}>Complete</button>
      <button onClick={() => onOpenChange(false)}>Cancel</button>
    </div>
  ) : null
}));

// Mock global fetch
global.fetch = vi.fn();

describe('LazySubtaskList', () => {
  const mockProjectId = 'project-123';
  const mockTaskTreeId = 'branch-123';
  const mockParentTaskId = 'task-123';

  const mockSubtasks = [
    {
      id: 'sub-1',
      title: 'Subtask 1',
      status: 'done',
      priority: 'high',
      assignees: ['user-1'],
      progress_percentage: 100,
      description: 'First subtask description',
      progress_notes: 'Completed successfully'
    },
    {
      id: 'sub-2',
      title: 'Subtask 2',
      status: 'in_progress',
      priority: 'medium',
      assignees: ['user-1', 'user-2'],
      progress_percentage: 50,
      description: 'Second subtask description'
    },
    {
      id: 'sub-3',
      title: 'Subtask 3',
      status: 'todo',
      priority: 'low',
      assignees: [],
      progress_percentage: 0
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (Cookies.get as ReturnType<typeof vi.fn>).mockReturnValue('test-token');
    (global.fetch as ReturnType<typeof vi.fn>).mockReset();
  });

  describe('Initial Loading', () => {
    it('should show loading state initially', () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      expect(screen.getByText('Loading subtasks...')).toBeInTheDocument();
    });

    it('should load subtasks from V2 endpoint successfully', async () => {
      const mockV2Response = {
        subtasks: mockSubtasks.map(sub => ({
          id: sub.id,
          title: sub.title,
          status: sub.status,
          priority: sub.priority,
          assignees_count: sub.assignees.length,
          progress_percentage: sub.progress_percentage
        })),
        parent_task_id: mockParentTaskId,
        total_count: 3,
        progress_summary: {
          total: 3,
          completed: 1,
          in_progress: 1,
          todo: 1,
          blocked: 0,
          completion_percentage: 33
        }
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockV2Response)
      });

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
        expect(screen.getByText('Subtask 2')).toBeInTheDocument();
        expect(screen.getByText('Subtask 3')).toBeInTheDocument();
      });

      expect(global.fetch).toHaveBeenCalledWith(
        `/api/v2/tasks/${mockParentTaskId}/subtasks/summaries`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ include_counts: true })
        })
      );
    });

    it('should fallback to regular API when V2 fails', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({})
      });

      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
        expect(screen.getByText('Subtask 2')).toBeInTheDocument();
        expect(screen.getByText('Subtask 3')).toBeInTheDocument();
      });

      expect(api.listSubtasks).toHaveBeenCalledWith(mockParentTaskId);
    });

    it('should handle authorization header when no token', async () => {
      (Cookies.get as ReturnType<typeof vi.fn>).mockReturnValue(null);
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({})
      });
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('No subtasks found.')).toBeInTheDocument();
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.any(String)
          })
        })
      );
    });

    it('should display error state', async () => {
      const errorMessage = 'Failed to load subtasks';
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error(errorMessage));

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(`Error loading subtasks: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    it('should handle empty subtask list', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('No subtasks found.')).toBeInTheDocument();
        expect(screen.getByText('Add Subtask')).toBeInTheDocument();
      });
    });
  });

  describe('Subtask Display', () => {
    beforeEach(async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
    });

    it('should display subtask information correctly', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        // Check subtask titles
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
        expect(screen.getByText('Subtask 2')).toBeInTheDocument();
        expect(screen.getByText('Subtask 3')).toBeInTheDocument();

        // Check statuses
        expect(screen.getByText('done')).toBeInTheDocument();
        expect(screen.getByText('in_progress')).toBeInTheDocument();
        expect(screen.getByText('todo')).toBeInTheDocument();

        // Check priorities
        expect(screen.getByText('high')).toBeInTheDocument();
        expect(screen.getByText('medium')).toBeInTheDocument();
        expect(screen.getByText('low')).toBeInTheDocument();

        // Check assignees
        expect(screen.getByText('1 assigned')).toBeInTheDocument();
        expect(screen.getByText('2 assigned')).toBeInTheDocument();
        expect(screen.getByText('Unassigned')).toBeInTheDocument();

        // Check progress percentages
        expect(screen.getByText('100%')).toBeInTheDocument();
        expect(screen.getByText('50%')).toBeInTheDocument();
      });
    });

    it('should display progress summary', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Progress:/)).toBeInTheDocument();
        expect(screen.getByText(/1\/3 completed \(33%\)/)).toBeInTheDocument();
        expect(screen.getByText('1 in progress')).toBeInTheDocument();
      });
    });

    it('should render table structure correctly', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(table).toBeInTheDocument();

        // Check table headers
        expect(screen.getByText('Subtask')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Priority')).toBeInTheDocument();
        expect(screen.getByText('Assignees')).toBeInTheDocument();
        expect(screen.getByText('Actions')).toBeInTheDocument();
      });
    });
  });

  describe('Subtask Details Dialog', () => {
    beforeEach(async () => {
      (apiLazy.getSubtaskSummaries as ReturnType<typeof vi.fn>).mockResolvedValue({
        subtasks: mockSummaries,
        total: 3
      });
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
      (api.getSubtask as ReturnType<typeof vi.fn>).mockImplementation((parentId, subtaskId) => {
        const subtask = mockSubtasks.find(s => s.id === subtaskId);
        return Promise.resolve(subtask || null);
      });
    });

    it('should open details dialog when clicking view button', async () => {
      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}`]
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      // Click view details button for first subtask
      const viewButtons = screen.getAllByTitle('View details');
      fireEvent.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('subtask-details-dialog')).toBeInTheDocument();
        expect(screen.getByText('Details for Subtask 1')).toBeInTheDocument();
        expect(screen.getByText('First subtask description')).toBeInTheDocument();
      });

      // Close dialog
      fireEvent.click(screen.getByText('Close'));

      await waitFor(() => {
        expect(screen.queryByTestId('subtask-details-dialog')).not.toBeInTheDocument();
      });
    });

    it('should open details dialog from URL parameter', async () => {
      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}/subtask/sub-1`]
      );

      await waitFor(() => {
        expect(screen.getByTestId('subtask-details-dialog')).toBeInTheDocument();
        expect(screen.getByText('Details for Subtask 1')).toBeInTheDocument();
      });
    });

    it('should handle subtask not found when opening from URL', async () => {
      (api.getSubtask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Subtask not found'));

      const mockNavigate = vi.fn();
      vi.doMock('react-router-dom', () => ({
        ...vi.importActual('react-router-dom'),
        useNavigate: () => mockNavigate
      }));

      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}/subtask/invalid-id`]
      );

      await waitFor(() => {
        expect(screen.queryByTestId('subtask-details-dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Subtask Actions', () => {
    beforeEach(async () => {
      (apiLazy.getSubtaskSummaries as ReturnType<typeof vi.fn>).mockResolvedValue({
        subtasks: mockSummaries,
        total: 3
      });
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
    });

    it('should handle subtask deletion', async () => {
      (api.deleteSubtask as ReturnType<typeof vi.fn>).mockResolvedValue(true);

      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}`]
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      // Click delete button for first subtask
      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
        expect(screen.getByText('Delete Subtask 1?')).toBeInTheDocument();
      });

      // Confirm deletion
      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(api.deleteSubtask).toHaveBeenCalledWith('sub-1');
      });
    });

    it('should handle delete failure gracefully', async () => {
      (api.deleteSubtask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Delete failed'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}`]
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(api.deleteSubtask).toHaveBeenCalled();
        expect(consoleSpy).toHaveBeenCalledWith('Failed to delete subtask:', expect.any(Error));
      });

      consoleSpy.mockRestore();
    });

    it('should cancel delete operation', async () => {
      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}`]
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      // Cancel deletion
      fireEvent.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(api.deleteSubtask).not.toHaveBeenCalled();
        expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
      });
    });

    it('should open complete dialog for incomplete subtasks', async () => {
      renderWithRouter(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />,
        [`/dashboard/project/${mockProjectId}/branch/${mockTaskTreeId}/task/${mockParentTaskId}`]
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 2')).toBeInTheDocument();
      });

      // Find complete button for second subtask (in_progress)
      const completeButtons = screen.getAllByTitle('Complete');
      fireEvent.click(completeButtons[1]); // Second subtask's complete button

      await waitFor(() => {
        expect(screen.getByTestId('subtask-complete-dialog')).toBeInTheDocument();
        expect(screen.getByText('Complete Subtask 2?')).toBeInTheDocument();
      });

      // Complete the subtask
      fireEvent.click(screen.getByText('Complete'));

      await waitFor(() => {
        expect(screen.queryByTestId('subtask-complete-dialog')).not.toBeInTheDocument();
      });
    });

    it('should not show complete button for done subtasks', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      // Complete buttons should only be available for non-done subtasks
      const completeButtons = screen.getAllByTitle('Complete');
      expect(completeButtons).toHaveLength(2); // Only for sub-2 and sub-3
    });

    it('should open edit dialog', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 2')).toBeInTheDocument();
      });

      // Click edit button for second subtask (not done)
      const editButtons = screen.getAllByTitle('Edit');
      fireEvent.click(editButtons[1]); // Second edit button

      await waitFor(() => {
        expect(screen.getByText('Edit Subtask')).toBeInTheDocument();
        expect(screen.getByText('Editing: Subtask 2')).toBeInTheDocument();
      });

      // Close edit dialog
      fireEvent.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(screen.queryByText('Edit Subtask')).not.toBeInTheDocument();
      });
    });

    it('should disable edit button for done subtasks', async () => {
      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByTitle('Edit');
      // First subtask is done, so edit button should be disabled
      expect(editButtons[0]).toBeDisabled();
    });
  });

  describe('Progress Bar', () => {
    it('should show correct progress percentage', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/33%/)).toBeInTheDocument();
      });

      // Check progress bar width
      const progressBar = document.querySelector('.bg-gradient-to-r.from-blue-400.to-blue-600');
      expect(progressBar).toHaveStyle({ width: '33%' });
    });

    it('should handle 100% completion', async () => {
      const allDoneSubtasks = mockSubtasks.map(sub => ({ ...sub, status: 'done' }));
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(allDoneSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/100%/)).toBeInTheDocument();
      });

      const progressBar = document.querySelector('.bg-gradient-to-r.from-blue-400.to-blue-600');
      expect(progressBar).toHaveStyle({ width: '100%' });
    });

    it('should handle 0% completion', async () => {
      const allTodoSubtasks = mockSubtasks.map(sub => ({ ...sub, status: 'todo' }));
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(allTodoSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/0%/)).toBeInTheDocument();
      });

      const progressBar = document.querySelector('.bg-gradient-to-r.from-blue-400.to-blue-600');
      expect(progressBar).toHaveStyle({ width: '0%' });
    });
  });

  describe('Add Subtask', () => {
    it('should show add subtask button when subtasks exist', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        const addButtons = screen.getAllByText('Add Subtask');
        expect(addButtons).toHaveLength(1); // One at the bottom
        expect(addButtons[0]).toHaveClass('border-blue-300');
      });
    });

    it('should show add subtask button when no subtasks', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('No subtasks found.')).toBeInTheDocument();
        const addButton = screen.getByText('Add Subtask');
        expect(addButton).toBeInTheDocument();
      });
    });
  });

  describe('Lazy Loading', () => {
    it('should only load once when component mounts', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      const { rerender } = render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      expect(api.listSubtasks).toHaveBeenCalledTimes(1);

      // Re-render with same props
      rerender(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      // Should not load again
      expect(api.listSubtasks).toHaveBeenCalledTimes(1);
    });

    it('should reload when parent task changes', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      const { rerender } = render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      expect(api.listSubtasks).toHaveBeenCalledTimes(1);

      // Change parent task ID
      rerender(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId="task-456"
        />
      );

      await waitFor(() => {
        expect(api.listSubtasks).toHaveBeenCalledTimes(2);
        expect(api.listSubtasks).toHaveBeenLastCalledWith('task-456');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle delete subtask errors gracefully', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
      (api.deleteSubtask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Delete failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to delete subtask:', expect.any(Error));
        expect(screen.getByText('Subtask 1')).toBeInTheDocument(); // Still exists
      });

      consoleSpy.mockRestore();
    });

    it('should handle load full subtask errors', async () => {
      // Set up initial summaries
      const summaryResponse = {
        subtasks: [{
          id: 'sub-1',
          title: 'Subtask 1',
          status: 'todo',
          priority: 'high',
          assignees_count: 1
        }]
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(summaryResponse)
      });

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtask 1')).toBeInTheDocument();
      });

      // Simulate error when loading full subtask
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Load failed'));

      const viewButtons = screen.getAllByTitle('View details');
      fireEvent.click(viewButtons[0]);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Status and Priority Colors', () => {
    it('should apply correct status colors', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([
        { ...mockSubtasks[0], status: 'done' },
        { ...mockSubtasks[1], status: 'in_progress' },
        { ...mockSubtasks[2], status: 'todo' },
        { id: 'sub-4', title: 'Sub 4', status: 'blocked', priority: 'high', assignees: [] },
        { id: 'sub-5', title: 'Sub 5', status: 'review', priority: 'medium', assignees: [] }
      ]);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        const badges = screen.getAllByRole('status');
        const statusBadges = badges.filter(badge => 
          ['done', 'in_progress', 'todo', 'blocked', 'review'].includes(badge.textContent || '')
        );

        expect(statusBadges).toHaveLength(5);
      });
    });

    it('should apply correct priority colors', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([
        { ...mockSubtasks[0], priority: 'urgent' },
        { ...mockSubtasks[1], priority: 'high' },
        { ...mockSubtasks[2], priority: 'medium' },
        { id: 'sub-4', title: 'Sub 4', status: 'todo', priority: 'low', assignees: [] }
      ]);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('urgent')).toBeInTheDocument();
        expect(screen.getByText('high')).toBeInTheDocument();
        expect(screen.getByText('medium')).toBeInTheDocument();
        expect(screen.getByText('low')).toBeInTheDocument();
      });
    });
  });

  describe('Subtask Section Styling', () => {
    it('should render section header with gradient lines', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtasks')).toBeInTheDocument();
        expect(screen.getByText('Subtasks')).toHaveClass('text-blue-600');
      });

      // Check for gradient lines
      const gradientLines = document.querySelectorAll('.h-px.flex-1.bg-gradient-to-r');
      expect(gradientLines).toHaveLength(2);
    });

    it('should have gradient background', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      const { container } = render(
        <LazySubtaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          parentTaskId={mockParentTaskId}
        />
      );

      await waitFor(() => {
        const backgroundDiv = container.querySelector('.bg-gradient-to-r.from-blue-50\\/30');
        expect(backgroundDiv).toBeInTheDocument();
      });
    });
  });
});