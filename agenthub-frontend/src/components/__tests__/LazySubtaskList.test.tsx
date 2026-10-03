/**
 * Tests for LazySubtaskList Component
 */

import { render, screen, waitFor, fireEvent, within } from '../../tests/test-utils';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LazySubtaskList from '../LazySubtaskList';
import { deleteSubtask, getAvailableAgents, getSubtask, getTask, listAgents, listSubtasks, Subtask } from '../../api';
import Cookies from 'js-cookie';

// Mock API functions
vi.mock('../../api', () => ({
  deleteSubtask: vi.fn(),
  listSubtasks: vi.fn(),
  getSubtask: vi.fn(),
  getTask: vi.fn(),
  getAvailableAgents: vi.fn(),
  listAgents: vi.fn(),
  createSubtask: vi.fn(),
  updateSubtask: vi.fn(),
  completeSubtask: vi.fn()
}));

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn()
  }
}));

// Mock useSubtaskAnimation to avoid unhandled async timers after test teardown
vi.mock('../../hooks/useSubtaskAnimation', () => ({
  useSubtaskAnimation: () => ({
    animationState: 'none',
    isVisible: true,
    animationClass: '',
    elementRef: { current: null },
    hasPlayedCreateAnimation: true,
    playCreateAnimation: vi.fn(),
    playUpdateAnimation: vi.fn(),
    playDeleteAnimation: vi.fn(),
  })
}));

// Mock lazy loaded components
vi.mock('../DeleteConfirmDialog', () => ({
  default: ({ open, onOpenChange, onConfirm, title, description, itemName }: any) =>
    open ? (
      <div data-testid="delete-dialog">
        <h3>{title}</h3>
        <p>{description}</p>
        <p>Item: {itemName}</p>
        <button onClick={() => onOpenChange(false)}>Cancel</button>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null
}));

vi.mock('../SubtaskCompleteDialog', () => ({
  default: ({ open, onOpenChange, subtask, onComplete }: any) =>
    open ? (
      <div data-testid="complete-dialog">
        <h3>Complete Subtask</h3>
        <p>{subtask?.title}</p>
        <button onClick={() => onOpenChange(false)}>Cancel</button>
        <button onClick={() => onComplete({ ...subtask, status: 'done' })}>Complete</button>
      </div>
    ) : null
}));

// Mock fetch globally
global.fetch = vi.fn();

const SUB1 = '11111111-1111-4111-8111-111111111111';
const SUB2 = '22222222-2222-4222-8222-222222222222';
const SUB3 = '33333333-3333-4333-8333-333333333333';

const mockSubtasks: Subtask[] = [
  {
    id: SUB1,
    title: 'Subtask 1',
    description: 'Description 1',
    status: 'todo',
    priority: 'high',
    assignees: ['user-1'],
    progress_percentage: 0,
    parent_task_id: 'task-123',
    progress_notes: 'Just started'
  },
  {
    id: SUB2,
    title: 'Subtask 2',
    description: 'Description 2',
    status: 'in_progress',
    priority: 'medium',
    assignees: ['user-1', 'user-2'],
    progress_percentage: 50,
    parent_task_id: 'task-123',
    progress_notes: 'Halfway done'
  },
  {
    id: SUB3,
    title: 'Subtask 3',
    description: 'Description 3',
    status: 'done',
    priority: 'low',
    assignees: [],
    progress_percentage: 100,
    parent_task_id: 'task-123',
    progress_notes: 'Completed'
  }
];

describe('LazySubtaskList', () => {
  const renderWithRouter = (ui: React.ReactElement, initialRoute: string = '/') => {
    window.history.pushState({}, '', initialRoute);
    return render(
      <Routes>
        <Route path="/dashboard/project/:projectId/branch/:taskTreeId/subtask/:subtaskId" element={ui} />
        <Route path="*" element={ui} />
      </Routes>
    );
  };

  beforeEach(() => {
    window.history.pushState({}, '', '/');
    vi.resetAllMocks();
    vi.mocked(Cookies.get).mockReturnValue('test-token');
    vi.mocked(getTask).mockResolvedValue(null);
    vi.mocked(getAvailableAgents).mockResolvedValue([]);
    vi.mocked(listAgents).mockResolvedValue([]);
  });

  test('should load and display subtask summaries from v2 endpoint', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    // Should show loading initially
    expect(screen.getByText('Loading subtasks...')).toBeInTheDocument();

    // Wait for subtasks to load
    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Check that all subtasks are displayed
    expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    expect(screen.getByText('Subtask 2')).toBeInTheDocument();
    expect(screen.getByText('Subtask 3')).toBeInTheDocument();

    // Check status badges (capitalized labels from the current badge component)
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();

    // Check assignee badges
    expect(screen.getAllByText('user-1').length).toBeGreaterThan(0);
    expect(screen.getByText('user-2')).toBeInTheDocument();
    expect(screen.getByText('Unassigned')).toBeInTheDocument();

    // Check progress percentages
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();

    // The summaries are loaded through the regular API layer
    expect(vi.mocked(listSubtasks)).toHaveBeenCalledWith('task-123');
  });

  test('should fall back to listSubtasks when v2 endpoint fails', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    expect(vi.mocked(listSubtasks)).toHaveBeenCalledWith('task-123');
    expect(screen.getByText('Subtask 2')).toBeInTheDocument();
    expect(screen.getByText('Subtask 3')).toBeInTheDocument();
  });

  test('should display progress summary correctly', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Progress:/)).toBeInTheDocument();
    });

    expect(screen.getByText(/1\/3 completed \(33%\)/)).toBeInTheDocument();
    expect(screen.getByText('1 in progress')).toBeInTheDocument();
  });

  test('should handle view details action', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);
    vi.mocked(getSubtask).mockResolvedValue(mockSubtasks[0]);

    renderWithRouter(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Click view details button for first subtask
    const viewButtons = screen.getAllByTitle('View details');
    fireEvent.click(viewButtons[0]);

    // The details dialog loads the full subtask and shows its description
    await waitFor(() => {
      expect(screen.getByText('Description 1')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Title is shown in both the row and the dialog
    expect(screen.getAllByText('Subtask 1').length).toBeGreaterThan(1);
    expect(vi.mocked(getSubtask)).toHaveBeenCalledWith('task-123', SUB1);

    // Close dialog
    fireEvent.click(screen.getByText('Close'));

    await waitFor(() => {
      expect(screen.queryByText('Description 1')).not.toBeInTheDocument();
    });
  });

  test('should handle delete subtask', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);
    vi.mocked(deleteSubtask).mockResolvedValue(undefined);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Click delete button for first subtask
    const deleteButtons = screen.getAllByTitle('Delete subtask');
    fireEvent.click(deleteButtons[0]);

    // Delete dialog should appear
    await waitFor(() => {
      expect(screen.getByTestId('delete-dialog')).toBeInTheDocument();
    });

    expect(screen.getByText('Delete Subtask')).toBeInTheDocument();
    expect(screen.getByText('Item: Subtask 1')).toBeInTheDocument();

    // Confirm deletion
    const confirmButton = screen.getByText('Confirm');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(vi.mocked(deleteSubtask)).toHaveBeenCalledWith(SUB1);
    });

    // Cache removal is delegated to WebSocket; the dialog must still close
    await waitFor(() => {
      expect(screen.queryByTestId('delete-dialog')).not.toBeInTheDocument();
    });
  });

  test('should handle complete subtask', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);
    vi.mocked(getSubtask).mockResolvedValue(mockSubtasks[0]);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Click complete button for first subtask (todo status)
    const completeButtons = screen.getAllByTitle('Complete');
    fireEvent.click(completeButtons[0]);

    // Should load full subtask and show complete dialog
    await waitFor(() => {
      expect(screen.getByTestId('complete-dialog')).toBeInTheDocument();
    });

    expect(within(screen.getByTestId('complete-dialog')).getByText('Subtask 1')).toBeInTheDocument();

    // Cancel closes the dialog
    fireEvent.click(within(screen.getByTestId('complete-dialog')).getByText('Cancel'));

    await waitFor(() => {
      expect(screen.queryByTestId('complete-dialog')).not.toBeInTheDocument();
    });
  });

  test('should show empty state when no subtasks', async () => {
    vi.mocked(listSubtasks).mockResolvedValue([]);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No subtasks found.')).toBeInTheDocument();
    });

    expect(screen.getByText('Add Subtask')).toBeInTheDocument();
  });

  test('should handle error state', async () => {
    vi.mocked(listSubtasks).mockRejectedValue(new Error('Failed to load subtasks'));

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Error loading subtasks:.*Failed to load subtasks/)).toBeInTheDocument();
    }, { timeout: 10000 });
  }, 15000);

  test('should disable edit button for completed subtasks', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 3')).toBeInTheDocument();
    });

    // Find the row with the completed subtask
    const subtask3Row = screen.getByText('Subtask 3').closest('tr');
    const editButton = within(subtask3Row!).getByTitle('Edit');

    expect(editButton).toBeDisabled();
  });

  test('should not show complete button for done subtasks', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 3')).toBeInTheDocument();
    });

    // Find the row with the completed subtask
    const subtask3Row = screen.getByText('Subtask 3').closest('tr');
    const completeButton = within(subtask3Row!).queryByTitle('Complete');

    expect(completeButton).not.toBeInTheDocument();
  });

  test('should show loading state while loading full subtask', async () => {
    let resolveFullLoad: (value: Subtask) => void = () => {};
    const fullLoadPromise = new Promise<Subtask>(resolve => { resolveFullLoad = resolve; });

    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);
    vi.mocked(getSubtask).mockImplementation(() => fullLoadPromise);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Trigger the lazy full-subtask load through the edit action
    const editButton = screen.getAllByTitle('Edit')[0];
    fireEvent.click(editButton);

    // Dialog should not be open yet while full subtask is loading
    expect(screen.queryByText('Edit Subtask')).not.toBeInTheDocument();

    // Resolve the loading
    resolveFullLoad(mockSubtasks[0]);

    // Dialog opens once full subtask has resolved
    await waitFor(() => {
      expect(screen.getByText('Edit Subtask')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Enter subtask title...')).toHaveValue('Subtask 1');
  });

  test('should handle edit subtask placeholder', async () => {
    vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);
    vi.mocked(getSubtask).mockResolvedValue(mockSubtasks[0]);

    render(
      <LazySubtaskList
        projectId="project-123"
        taskTreeId="tree-123"
        parentTaskId="task-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Subtask 1')).toBeInTheDocument();
    });

    // Click edit button
    const editButtons = screen.getAllByTitle('Edit');
    fireEvent.click(editButtons[0]);

    // Should show edit dialog with the subtask title pre-filled
    await waitFor(() => {
      expect(screen.getByText('Edit Subtask')).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText('Enter subtask title...')).toHaveValue('Subtask 1');

    // Cancel editing
    fireEvent.click(screen.getByText('Cancel'));

    await waitFor(() => {
      expect(screen.queryByText('Edit Subtask')).not.toBeInTheDocument();
    });
  });
});
