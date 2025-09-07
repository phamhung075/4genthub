import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import LazyTaskList from './LazyTaskList';
import * as api from '../api';

// Mock the API module
vi.mock('../api', () => ({
  listTasks: vi.fn(),
  updateTask: vi.fn(),
  getTaskContext: vi.fn(),
  listAgents: vi.fn(),
  getAvailableAgents: vi.fn(),
  callAgent: vi.fn(),
  createTask: vi.fn(),
  completeTask: vi.fn(),
  deleteTask: vi.fn(),
}));

// Mock lazy-loaded components
vi.mock('./LazySubtaskList', () => ({
  __esModule: true,
  default: ({ parentTaskId }: any) => <div data-testid={`subtasks-${parentTaskId}`}>Subtasks for {parentTaskId}</div>
}));

vi.mock('./TaskDetailsDialog', () => ({
  __esModule: true,
  default: ({ open, task, onClose }: any) => open ? (
    <div data-testid="task-details-dialog">
      <h3>Task Details: {task?.title}</h3>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('./TaskEditDialog', () => ({
  __esModule: true,
  default: ({ open, task, onClose, onSave }: any) => open ? (
    <div data-testid="task-edit-dialog">
      <h3>Edit Task: {task?.title || 'New Task'}</h3>
      <button onClick={onClose}>Cancel</button>
      <button onClick={onSave}>Save</button>
    </div>
  ) : null
}));

vi.mock('./AgentAssignmentDialog', () => ({
  __esModule: true,
  default: ({ open, task, onClose, agents, availableAgents }: any) => open ? (
    <div data-testid="agent-assignment-dialog">
      <h3>Assign Agents to: {task?.title}</h3>
      <div>Available agents: {availableAgents?.length || 0}</div>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('./TaskContextDialog', () => ({
  __esModule: true,
  default: ({ open, task, context, onClose, loading }: any) => open ? (
    <div data-testid="task-context-dialog">
      <h3>Task Context: {task?.title}</h3>
      {loading ? <div>Loading context...</div> : <div>Context loaded</div>}
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('./TaskCompleteDialog', () => ({
  __esModule: true,
  default: ({ open, onClose }: any) => open ? (
    <div data-testid="task-complete-dialog">
      <h3>Complete Task</h3>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

vi.mock('./DeleteConfirmDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange, onConfirm, itemName }: any) => open ? (
    <div data-testid="delete-confirm-dialog">
      <h3>Delete Task: {itemName}</h3>
      <button onClick={() => onOpenChange(false)}>Cancel</button>
      <button onClick={onConfirm}>Delete</button>
    </div>
  ) : null
}));

vi.mock('./AgentResponseDialog', () => ({
  __esModule: true,
  default: ({ open, onClose }: any) => open ? (
    <div data-testid="agent-response-dialog">
      <h3>Agent Response</h3>
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}));

// Mock TaskSearch component
vi.mock('./TaskSearch', () => ({
  __esModule: true,
  default: ({ onTaskSelect, onSubtaskSelect }: any) => (
    <div data-testid="task-search">
      <input placeholder="Search tasks..." />
      <button onClick={() => onTaskSelect({ id: 'task-1', title: 'Test Task' })}>
        Select Task
      </button>
    </div>
  )
}));

describe('LazyTaskList', () => {
  const mockProjectId = 'project-123';
  const mockTaskTreeId = 'branch-456';
  const mockOnTasksChanged = vi.fn();

  const mockTasks = [
    {
      id: 'task-1',
      title: 'Test Task 1',
      status: 'todo',
      priority: 'high',
      subtasks: [{ id: 'subtask-1' }],
      assignees: ['user-1'],
      dependencies: [],
      context_id: 'context-1'
    },
    {
      id: 'task-2',
      title: 'Test Task 2',
      status: 'in_progress',
      priority: 'medium',
      subtasks: [],
      assignees: [],
      dependencies: ['task-1'],
      context_id: null
    },
    {
      id: 'task-3',
      title: 'Test Task 3',
      status: 'done',
      priority: 'low',
      subtasks: [],
      assignees: ['user-1', 'user-2'],
      dependencies: [],
      context_id: null
    }
  ];

  const mockAgents = [
    { id: 'agent-1', name: 'Test Agent 1' },
    { id: 'agent-2', name: 'Test Agent 2' }
  ];

  const mockAvailableAgents = ['@agent1', '@agent2', '@agent3'];

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Set up default mocks
    (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
    (api.listAgents as ReturnType<typeof vi.fn>).mockResolvedValue(mockAgents);
    (api.getAvailableAgents as ReturnType<typeof vi.fn>).mockResolvedValue(mockAvailableAgents);
    (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue({ data: 'test context' });
    (api.deleteTask as ReturnType<typeof vi.fn>).mockResolvedValue(true);
    
    // Mock window.innerWidth for responsive tests
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  it('renders loading state initially', () => {
    render(
      <LazyTaskList
        projectId={mockProjectId}
        taskTreeId={mockTaskTreeId}
        onTasksChanged={mockOnTasksChanged}
      />
    );

    expect(screen.getByText('Loading tasks...')).toBeInTheDocument();
  });

  it('renders tasks after loading', async () => {
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
      expect(screen.getByText('Test Task 3')).toBeInTheDocument();
    });

    // Check task count
    expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
  });

  it('renders error state when loading fails', async () => {
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

  it('displays task badges correctly', async () => {
    render(
      <LazyTaskList
        projectId={mockProjectId}
        taskTreeId={mockTaskTreeId}
        onTasksChanged={mockOnTasksChanged}
      />
    );

    await waitFor(() => {
      // Status badges
      expect(screen.getByText('todo')).toBeInTheDocument();
      expect(screen.getByText('in_progress')).toBeInTheDocument();
      expect(screen.getByText('done')).toBeInTheDocument();

      // Priority badges
      expect(screen.getByText('high')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByText('low')).toBeInTheDocument();

      // Subtask count badge
      expect(screen.getByText('1')).toBeInTheDocument();

      // Dependencies badge
      expect(screen.getByText('Has dependencies')).toBeInTheDocument();

      // Assignees badges
      expect(screen.getByText('1 assigned')).toBeInTheDocument();
      expect(screen.getByText('2 assigned')).toBeInTheDocument();
    });
  });

  it('expands and collapses tasks to show subtasks', async () => {
    const user = userEvent.setup();
    
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
    const expandButtons = screen.getAllByRole('button', { name: '' });
    const firstExpandButton = expandButtons[0];

    // Click to expand
    await user.click(firstExpandButton);

    await waitFor(() => {
      expect(screen.getByTestId('subtasks-task-1')).toBeInTheDocument();
    });

    // Click to collapse
    await user.click(firstExpandButton);

    await waitFor(() => {
      expect(screen.queryByTestId('subtasks-task-1')).not.toBeInTheDocument();
    });
  });

  it('opens task details dialog when view button is clicked', async () => {
    const user = userEvent.setup();
    
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

    // Find and click the view button (Eye icon)
    const viewButtons = screen.getAllByTitle('View details');
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('task-details-dialog')).toBeInTheDocument();
      expect(screen.getByText('Task Details: Test Task 1')).toBeInTheDocument();
    });

    // Close the dialog
    await user.click(screen.getByText('Close'));
    expect(screen.queryByTestId('task-details-dialog')).not.toBeInTheDocument();
  });

  it('opens edit dialog when edit button is clicked', async () => {
    const user = userEvent.setup();
    
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

    // Find and click the edit button
    const editButtons = screen.getAllByTitle('Edit task');
    await user.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('task-edit-dialog')).toBeInTheDocument();
      expect(screen.getByText('Edit Task: Test Task 1')).toBeInTheDocument();
    });
  });

  it('opens create dialog when new task button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <LazyTaskList
        projectId={mockProjectId}
        taskTreeId={mockTaskTreeId}
        onTasksChanged={mockOnTasksChanged}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('New Task')).toBeInTheDocument();
    });

    await user.click(screen.getByText('New Task'));

    await waitFor(() => {
      expect(screen.getByTestId('task-edit-dialog')).toBeInTheDocument();
      expect(screen.getByText('Edit Task: New Task')).toBeInTheDocument();
    });
  });

  it('opens agent assignment dialog and loads agents', async () => {
    const user = userEvent.setup();
    
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

    // Find and click the assign button
    const assignButtons = screen.getAllByTitle('Assign agents');
    await user.click(assignButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('agent-assignment-dialog')).toBeInTheDocument();
      expect(screen.getByText('Assign Agents to: Test Task 1')).toBeInTheDocument();
      expect(screen.getByText('Available agents: 3')).toBeInTheDocument();
    });

    // Verify agents were loaded
    expect(api.listAgents).toHaveBeenCalledWith(mockProjectId);
    expect(api.getAvailableAgents).toHaveBeenCalled();
  });

  it('opens context dialog for tasks with context', async () => {
    const user = userEvent.setup();
    
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

    // Find and click the context button (only task-1 has context)
    const contextButtons = screen.getAllByTitle('View context');
    expect(contextButtons).toHaveLength(1); // Only one task has context
    await user.click(contextButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('task-context-dialog')).toBeInTheDocument();
      expect(screen.getByText('Task Context: Test Task 1')).toBeInTheDocument();
    });
  });

  it('handles task deletion', async () => {
    const user = userEvent.setup();
    
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

    // Find and click the delete button
    const deleteButtons = screen.getAllByTitle('Delete task');
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByText('Delete Task: Test Task 1')).toBeInTheDocument();
    });

    // Confirm deletion
    await user.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(api.deleteTask).toHaveBeenCalledWith('task-1');
      expect(mockOnTasksChanged).toHaveBeenCalled();
    });

    // Task should be removed from the list
    expect(screen.queryByText('Test Task 1')).not.toBeInTheDocument();
  });

  it('refreshes task list when refresh button is clicked', async () => {
    const user = userEvent.setup();
    
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

    // Clear the mock to track new calls
    (api.listTasks as ReturnType<typeof vi.fn>).mockClear();

    // Find and click the refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    expect(api.listTasks).toHaveBeenCalledWith({ git_branch_id: mockTaskTreeId });
  });

  it('renders mobile view on small screens', async () => {
    // Set window width to mobile size
    window.innerWidth = 500;
    fireEvent(window, new Event('resize'));

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

    // In mobile view, tasks should be in cards, not table
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    
    // Mobile-specific elements
    expect(screen.getByText('New')).toBeInTheDocument(); // Shortened button text
    expect(screen.getAllByText('View')).toHaveLength(3); // View buttons for each task
    expect(screen.getAllByText('Edit')).toHaveLength(3); // Edit buttons for each task
    expect(screen.getAllByText('Assign')).toHaveLength(3); // Assign buttons for each task
  });

  it('handles empty task list', async () => {
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

    // Should still show the new task button
    expect(screen.getByText('New Task')).toBeInTheDocument();
  });

  it('handles search functionality', async () => {
    const user = userEvent.setup();
    
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

    // Click the search select button
    await user.click(screen.getByText('Select Task'));

    // Should open task details dialog
    await waitFor(() => {
      expect(screen.getByTestId('task-details-dialog')).toBeInTheDocument();
      expect(screen.getByText('Task Details: Test Task')).toBeInTheDocument();
    });
  });

  it('handles invalid task list response gracefully', async () => {
    // Mock an invalid response (not an array)
    (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue({ invalid: 'response' });

    render(
      <LazyTaskList
        projectId={mockProjectId}
        taskTreeId={mockTaskTreeId}
        onTasksChanged={mockOnTasksChanged}
      />
    );

    await waitFor(() => {
      // Should handle gracefully and show empty list
      expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
    });
  });

  it('loads full task data when expanding', async () => {
    const user = userEvent.setup();
    
    // Mock fetch for individual task loading
    global.fetch = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue(mockTasks[0])
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

    // Expand the first task
    const expandButtons = screen.getAllByRole('button', { name: '' });
    await user.click(expandButtons[0]);

    // Should show subtasks
    await waitFor(() => {
      expect(screen.getByTestId('subtasks-task-1')).toBeInTheDocument();
    });
  });

  it('shows loading spinner when expanding task', async () => {
    const user = userEvent.setup();
    
    // Mock a slow fetch
    global.fetch = vi.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        json: vi.fn().mockResolvedValue(mockTasks[0])
      }), 100))
    );

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

    // Click expand - should show spinner
    const expandButtons = screen.getAllByRole('button', { name: '' });
    await user.click(expandButtons[0]);

    // Look for the spinner (animated element)
    const spinner = expandButtons[0].querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('caches loaded task contexts', async () => {
    const user = userEvent.setup();
    
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

    // Open context dialog
    const contextButton = screen.getByTitle('View context');
    await user.click(contextButton);

    await waitFor(() => {
      expect(api.getTaskContext).toHaveBeenCalledWith('task-1');
    });

    // Close and reopen - should not fetch again
    await user.click(screen.getByText('Close'));
    (api.getTaskContext as ReturnType<typeof vi.fn>).mockClear();
    
    await user.click(contextButton);
    
    expect(api.getTaskContext).not.toHaveBeenCalled();
  });
});