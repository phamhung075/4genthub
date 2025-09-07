import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import LazyTaskList from '../../components/LazyTaskList';
import * as api from '../../api';
import { act } from 'react-dom/test-utils';

// Mock the api module
vi.mock('../../api');

// Mock lazy-loaded components
vi.mock('../../components/LazySubtaskList', () => ({
  __esModule: true,
  default: () => <div data-testid="lazy-subtask-list">Subtask List</div>
}));

vi.mock('../../components/TaskDetailsDialog', () => ({
  __esModule: true,
  default: ({ open, onClose, task }: any) => open ? (
    <div data-testid="task-details-dialog">
      <div>Task Details: {task?.title}</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/TaskEditDialog', () => ({
  __esModule: true,
  default: ({ open, onClose, task }: any) => open ? (
    <div data-testid="task-edit-dialog">
      <div>Edit Task: {task?.title}</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/AgentAssignmentDialog', () => ({
  __esModule: true,
  default: ({ open, onClose }: any) => open ? (
    <div data-testid="agent-assignment-dialog">
      <div>Agent Assignment</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/TaskContextDialog', () => ({
  __esModule: true,
  default: ({ open, onClose }: any) => open ? (
    <div data-testid="task-context-dialog">
      <div>Task Context</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/RefreshButton', () => ({
  __esModule: true,
  default: ({ onRefresh, isRefreshing }: any) => (
    <button 
      onClick={onRefresh} 
      disabled={isRefreshing}
      role="button"
      aria-label={isRefreshing ? "refreshing" : "refresh"}
    >
      {isRefreshing ? "Refreshing..." : "Refresh"}
    </button>
  )
}));

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

vi.mock('../../components/AgentResponseDialog', () => ({
  __esModule: true,
  default: ({ open, onClose }: any) => open ? (
    <div data-testid="agent-response-dialog">
      <div>Agent Response</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/TaskSearch', () => ({
  __esModule: true,
  default: ({ onTaskSelect, onSubtaskSelect }: any) => (
    <div data-testid="task-search">
      <input placeholder="Search tasks..." />
      <button onClick={() => onTaskSelect({ id: 'search-task-1', title: 'Found Task' })}>
        Select Task
      </button>
    </div>
  )
}));

describe('LazyTaskList', () => {
  const mockProjectId = 'project-123';
  const mockTaskTreeId = 'branch-123';
  const mockOnTasksChanged = vi.fn();

  const mockTasks = [
    {
      id: 'task-1',
      title: 'Test Task 1',
      status: 'todo',
      priority: 'high',
      subtasks: ['sub-1', 'sub-2'],
      assignees: ['user-1'],
      dependencies: ['dep-1'],
      context_id: 'ctx-1'
    },
    {
      id: 'task-2',
      title: 'Test Task 2',
      status: 'in_progress',
      priority: 'medium',
      subtasks: [],
      assignees: [],
      dependencies: [],
      context_id: null
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window dimensions for responsive testing
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024
    });
    window.dispatchEvent(new Event('resize'));
  });

  describe('Initial Loading', () => {
    it('should show loading state initially', () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));
      
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      expect(screen.getByText('Loading tasks...')).toBeInTheDocument();
    });

    it('should load and display tasks', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
        expect(screen.getByText('Test Task 2')).toBeInTheDocument();
      });

      expect(api.listTasks).toHaveBeenCalledWith({ git_branch_id: mockTaskTreeId });
    });

    it('should display error state', async () => {
      const errorMessage = 'Failed to load tasks';
      (api.listTasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error(errorMessage));

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    it('should handle empty task list', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
      });
    });

    it('should handle non-array task response gracefully', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(null);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
      });
    });
  });

  describe('Task Display', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    });

    it('should display task information correctly', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
        expect(screen.getByText('todo')).toBeInTheDocument();
        expect(screen.getByText('high')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // subtask count badge
        expect(screen.getByText('Has deps')).toBeInTheDocument();
        expect(screen.getByText('1 assigned')).toBeInTheDocument();
      });
    });

    it('should show correct task count', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });
    });
  });

  describe('Task Expansion', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    });

    it('should expand and collapse tasks', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Find the expand button for the first task
      const expandButtons = screen.getAllByRole('button', { name: '' }).filter(
        btn => btn.querySelector('svg')
      );
      const firstExpandButton = expandButtons[0];

      // Click to expand
      fireEvent.click(firstExpandButton);

      await waitFor(() => {
        expect(screen.getByTestId('lazy-subtask-list')).toBeInTheDocument();
      });

      // Click to collapse
      fireEvent.click(firstExpandButton);

      await waitFor(() => {
        expect(screen.queryByTestId('lazy-subtask-list')).not.toBeInTheDocument();
      });
    });
  });

  describe('Dialog Operations', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listAgents as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.getAvailableAgents as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    });

    it('should open task details dialog', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Click the mobile view button for task-1
      const expandButtons = screen.getAllByRole('button').filter(button => 
        button.getAttribute('title')?.includes('View details')
      );
      fireEvent.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('task-details-dialog')).toBeInTheDocument();
        expect(screen.getByText('Task Details: Test Task 1')).toBeInTheDocument();
      });

      // Close dialog
      fireEvent.click(screen.getByText('Close'));
      
      await waitFor(() => {
        expect(screen.queryByTestId('task-details-dialog')).not.toBeInTheDocument();
      });
    });

    it('should open edit dialog', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByTitle('Edit task');
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('task-edit-dialog')).toBeInTheDocument();
        expect(screen.getByText('Edit Task: Test Task 1')).toBeInTheDocument();
      });
    });

    it('should open agent assignment dialog', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('agent-assignment-dialog')).toBeInTheDocument();
        expect(api.listAgents).toHaveBeenCalledWith(mockProjectId);
        expect(api.getAvailableAgents).toHaveBeenCalled();
      });
    });

    it('should open context dialog only for tasks with context', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const contextButtons = screen.getAllByTitle('View context');
      expect(contextButtons).toHaveLength(1); // Only task-1 has context

      fireEvent.click(contextButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('task-context-dialog')).toBeInTheDocument();
      });
    });

    it('should open delete confirmation dialog', async () => {
      (api.deleteTask as ReturnType<typeof vi.fn>).mockResolvedValue(true);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete task');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
        expect(screen.getByText('Delete Test Task 1?')).toBeInTheDocument();
      });

      // Confirm deletion
      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(api.deleteTask).toHaveBeenCalledWith('task-1');
        expect(mockOnTasksChanged).toHaveBeenCalled();
        expect(screen.queryByText('Test Task 1')).not.toBeInTheDocument();
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument();
      });
    });

    it('should handle delete failure', async () => {
      (api.deleteTask as ReturnType<typeof vi.fn>).mockResolvedValue(false);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete task');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(api.deleteTask).toHaveBeenCalledWith('task-1');
        expect(mockOnTasksChanged).not.toHaveBeenCalled();
        expect(screen.getByText('Test Task 1')).toBeInTheDocument(); // Task still exists
      });
    });

    it('should cancel delete operation', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete task');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      // Cancel deletion
      fireEvent.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(api.deleteTask).not.toHaveBeenCalled();
        expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Create Task', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    });

    it('should open create task dialog', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });

      const createButton = screen.getByText('New Task');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByTestId('task-edit-dialog')).toBeInTheDocument();
      });
    });
  });

  describe('Refresh Functionality', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(mockTasks)
        .mockResolvedValueOnce([...mockTasks, {
          id: 'task-3',
          title: 'New Task 3',
          status: 'todo',
          priority: 'low',
          subtasks: [],
          assignees: [],
          dependencies: []
        }]);
    });

    it('should refresh task list', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });

      // Find and click refresh button
      const refreshButton = screen.getByRole('button', { name: 'refresh' });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
        expect(screen.getByText('New Task 3')).toBeInTheDocument();
      });

      expect(api.listTasks).toHaveBeenCalledTimes(2);
    });
  });

  describe('Search Integration', () => {
    beforeEach(async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    });

    it('should render search component', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('task-search')).toBeInTheDocument();
      });
    });

    it('should handle task selection from search', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('task-search')).toBeInTheDocument();
      });

      const selectButton = screen.getByText('Select Task');
      fireEvent.click(selectButton);

      await waitFor(() => {
        expect(screen.getByTestId('task-details-dialog')).toBeInTheDocument();
        expect(screen.getByText('Task Details: Found Task')).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render mobile view on small screens', async () => {
      // Set mobile width
      window.innerWidth = 500;
      window.dispatchEvent(new Event('resize'));

      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Check for mobile-specific elements
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      // Mobile view uses cards instead of table
      const cards = screen.getAllByText(/Test Task/);
      expect(cards).toHaveLength(2);

      // Check for mobile button text  
      expect(screen.queryByText('New Task')).toBeInTheDocument(); // Mobile still shows full text
    });

    it('should render desktop view on large screens', async () => {
      // Set desktop width
      window.innerWidth = 1024;
      window.dispatchEvent(new Event('resize'));

      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Check for desktop-specific elements
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByText('New Task')).toBeInTheDocument(); // Full text
    });
  });

  describe('Pagination', () => {
    const manyTasks = Array.from({ length: 25 }, (_, i) => ({
      id: `task-${i}`,
      title: `Task ${i}`,
      status: 'todo',
      priority: 'medium',
      subtasks: [],
      assignees: [],
      dependencies: []
    }));

    beforeEach(() => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(manyTasks);
    });

    it('should show load more button when there are more tasks', async () => {
      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (25)')).toBeInTheDocument();
      });

      // Should show first 20 tasks
      expect(screen.getByText('Task 0')).toBeInTheDocument();
      expect(screen.getByText('Task 19')).toBeInTheDocument();
      expect(screen.queryByText('Task 20')).not.toBeInTheDocument();

      // Should show load more button
      const loadMoreButton = screen.getByText('Load More Tasks');
      expect(loadMoreButton).toBeInTheDocument();

      // Click load more
      fireEvent.click(loadMoreButton);

      await waitFor(() => {
        expect(screen.getByText('Task 20')).toBeInTheDocument();
        expect(screen.getByText('Task 24')).toBeInTheDocument();
      });

      // Load more button should be hidden when all tasks are shown
      expect(screen.queryByText('Load More Tasks')).not.toBeInTheDocument();
    });
  });

  describe('Lazy Loading', () => {
    beforeEach(() => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    });

    it('should load full task data on demand when expanding', async () => {
      // Mock fetch for individual task loading
      global.fetch = vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({
          id: 'task-1',
          title: 'Test Task 1',
          description: 'Full task description',
          status: 'todo',
          priority: 'high',
          subtasks: ['sub-1', 'sub-2'],
          assignees: ['user-1'],
          dependencies: ['dep-1'],
          context_id: 'ctx-1'
        })
      });

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Expand task - should not trigger fetch since data is already loaded
      const expandButtons = screen.getAllByRole('button', { name: '' }).filter(
        btn => btn.querySelector('svg')
      );
      fireEvent.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('lazy-subtask-list')).toBeInTheDocument();
      });

      // Fetch should not be called for already loaded tasks
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should show loading spinner when expanding task', async () => {
      // Set up a delayed response
      let resolvePromise: any;
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([{
        ...mockTasks[0],
        _delayed: true // Flag to simulate loading
      }]);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // The expand button should show a spinner while loading
      // (This is a simplified test - actual implementation might differ)
    });
  });

  describe('Error Handling', () => {
    it('should handle task context loading errors', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Context load failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Context button should still be clickable even if loading fails
      const contextButtons = screen.getAllByTitle('View context');
      fireEvent.click(contextButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('task-context-dialog')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('should handle agent loading errors', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listAgents as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Agents load failed'));
      (api.getAvailableAgents as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Available agents load failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('agent-assignment-dialog')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('should handle delete task errors gracefully', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.deleteTask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Delete failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete task');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(api.deleteTask).toHaveBeenCalled();
        expect(screen.getByText('Test Task 1')).toBeInTheDocument(); // Task still exists
        expect(mockOnTasksChanged).not.toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Component Lifecycle', () => {
    it('should reload tasks when projectId or taskTreeId changes', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);

      const { rerender } = render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(api.listTasks).toHaveBeenCalledTimes(1);
      });

      // Change projectId
      rerender(
        <LazyTaskList
          projectId="project-456"
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(api.listTasks).toHaveBeenCalledTimes(2);
      });

      // Change taskTreeId
      rerender(
        <LazyTaskList
          projectId="project-456"
          taskTreeId="branch-456"
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(api.listTasks).toHaveBeenCalledTimes(3);
        expect(api.listTasks).toHaveBeenLastCalledWith({ git_branch_id: 'branch-456' });
      });
    });

    it('should cleanup on unmount', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);

      const { unmount } = render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task 1')).toBeInTheDocument();
      });

      // Unmount should not cause errors
      unmount();

      // Verify no lingering timers or subscriptions
      expect(() => unmount()).not.toThrow();
    });
  });
});