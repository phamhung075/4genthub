/**
 * Tests for LazySubtaskList Component
 */

import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import LazySubtaskList from '../LazySubtaskList';
import { deleteSubtask, listSubtasks, Subtask } from '../../api';
import Cookies from 'js-cookie';

// Mock API functions
vi.mock('../../api', () => ({
  deleteSubtask: vi.fn(),
  listSubtasks: vi.fn(),
  createSubtask: vi.fn(),
  updateSubtask: vi.fn(),
  completeSubtask: vi.fn()
}));

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn()
  }
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

const mockSubtasks: Subtask[] = [
  {
    id: 'sub-1',
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
    id: 'sub-2',
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
    id: 'sub-3',
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

const mockSubtaskSummariesResponse = {
  subtasks: [
    {
      id: 'sub-1',
      title: 'Subtask 1',
      status: 'todo',
      priority: 'high',
      assignees_count: 1,
      progress_percentage: 0
    },
    {
      id: 'sub-2',
      title: 'Subtask 2',
      status: 'in_progress',
      priority: 'medium',
      assignees_count: 2,
      progress_percentage: 50
    },
    {
      id: 'sub-3',
      title: 'Subtask 3',
      status: 'done',
      priority: 'low',
      assignees_count: 0,
      progress_percentage: 100
    }
  ],
  parent_task_id: 'task-123',
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

describe('LazySubtaskList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(Cookies.get).mockReturnValue('test-token');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('should load and display subtask summaries from v2 endpoint', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });

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

    // Check status badges
    expect(screen.getByText('todo')).toBeInTheDocument();
    expect(screen.getByText('in_progress')).toBeInTheDocument();
    expect(screen.getByText('done')).toBeInTheDocument();

    // Check assignee counts
    expect(screen.getByText('1 assigned')).toBeInTheDocument();
    expect(screen.getByText('2 assigned')).toBeInTheDocument();
    expect(screen.getByText('Unassigned')).toBeInTheDocument();

    // Check progress percentages
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();

    // Check API call was made with auth header
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v2/tasks/task-123/subtasks/summaries',
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

  test('should fall back to listSubtasks when v2 endpoint fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('API error'));
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
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });

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
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });
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

    // Click view details button for first subtask
    const viewButtons = screen.getAllByTitle('View details');
    fireEvent.click(viewButtons[0]);

    // Should load full subtask data and show details
    await waitFor(() => {
      expect(screen.getByText(/Description:.*Description 1/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Assignees:.*user-1/)).toBeInTheDocument();
    expect(screen.getByText(/Progress Notes:.*Just started/)).toBeInTheDocument();
  });

  test('should handle delete subtask', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });
    vi.mocked(deleteSubtask).mockResolvedValue(true);

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
      expect(vi.mocked(deleteSubtask)).toHaveBeenCalledWith('task-123', 'sub-1');
    });

    // Subtask should be removed from list
    await waitFor(() => {
      expect(screen.queryByText('Subtask 1')).not.toBeInTheDocument();
    });
  });

  test('should handle complete subtask', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });
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

    // Click complete button for first subtask (todo status)
    const completeButtons = screen.getAllByTitle('Complete');
    fireEvent.click(completeButtons[0]);

    // Should load full subtask and show complete dialog
    await waitFor(() => {
      expect(screen.getByTestId('complete-dialog')).toBeInTheDocument();
    });

    // Complete the subtask
    const completeButton = within(screen.getByTestId('complete-dialog')).getByText('Complete');
    fireEvent.click(completeButton);

    // Check that status is updated to done
    await waitFor(() => {
      const todoElements = screen.queryAllByText('todo');
      expect(todoElements).toHaveLength(0);
    });
  });

  test('should show empty state when no subtasks', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        subtasks: [],
        parent_task_id: 'task-123',
        total_count: 0,
        progress_summary: {
          total: 0,
          completed: 0,
          in_progress: 0,
          todo: 0,
          blocked: 0,
          completion_percentage: 0
        }
      })
    });

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
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
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
    });
  });

  test('should disable edit button for completed subtasks', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });

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
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });

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

  test('should show loading spinner when loading full subtask', async () => {
    let resolveFullLoad: any;
    const fullLoadPromise = new Promise(resolve => { resolveFullLoad = resolve; });
    
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });
    
    vi.mocked(listSubtasks).mockImplementation(() => fullLoadPromise as any);

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

    // Click view details button
    const viewButton = screen.getAllByTitle('View details')[0];
    fireEvent.click(viewButton);

    // Should show loading spinner
    await waitFor(() => {
      const button = screen.getAllByTitle('View details')[0];
      expect(button.querySelector('.animate-spin')).toBeInTheDocument();
    });

    // Resolve the loading
    resolveFullLoad(mockSubtasks);

    // Loading spinner should disappear
    await waitFor(() => {
      const button = screen.getAllByTitle('View details')[0];
      expect(button.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });

  test('should handle edit subtask placeholder', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSubtaskSummariesResponse
    });
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

    // Click edit button
    const editButtons = screen.getAllByTitle('Edit');
    fireEvent.click(editButtons[0]);

    // Should show edit dialog placeholder
    await waitFor(() => {
      expect(screen.getByText('Edit Subtask')).toBeInTheDocument();
    });

    expect(screen.getByText('Editing: Subtask 1')).toBeInTheDocument();

    // Cancel editing
    fireEvent.click(screen.getByText('Cancel'));

    await waitFor(() => {
      expect(screen.queryByText('Edit Subtask')).not.toBeInTheDocument();
    });
  });
});