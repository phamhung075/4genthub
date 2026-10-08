import React from 'react';
import { render, screen, fireEvent, waitFor } from './../test-utils';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { TaskSearch } from '../../components/TaskSearch';
import * as api from '../../api';
import type { Task } from '../../api';
import logger from '../../utils/logger';

// Mock the api module
vi.mock('../../api');

// Mock debounce to execute immediately in tests, keeping the real cn() helper
vi.mock('../../lib/utils', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/utils')>();
  return {
    ...actual,
    debounce: (fn: any) => fn
  };
});

describe('TaskSearch', () => {
  const mockProjectId = 'project-123';
  const mockTaskTreeId = 'branch-123';
  const mockOnTaskSelect = vi.fn();
  const mockOnSubtaskSelect = vi.fn();

  const mockTasks = [
    {
      id: 'task-1',
      title: 'Implement authentication',
      status: 'in_progress',
      priority: 'high',
      subtasks: ['sub-1', 'sub-2']
    },
    {
      id: 'task-2',
      title: 'Fix login bug',
      status: 'todo',
      priority: 'urgent'
    }
  ];

  const mockSubtasks = [
    {
      id: 'sub-1',
      title: 'Create login form',
      status: 'done',
      priority: 'medium',
      description: 'Design and implement login form'
    },
    {
      id: 'sub-2',
      title: 'Add authentication validation',
      status: 'in_progress',
      priority: 'high'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('Component Rendering', () => {
    it('should render search input with placeholder', () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveAttribute('type', 'text');
    });

    it('should display search icon', () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchIcon = document.querySelector('.lucide-search');
      expect(searchIcon).toBeInTheDocument();
    });

    it('should not show results initially', () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      expect(screen.queryByText('No results found')).not.toBeInTheDocument();
      expect(screen.queryByText('Searching...')).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('should search tasks when typing', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(api.searchTasks).toHaveBeenCalledWith('auth', { git_branch_id: mockTaskTreeId });
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });
    });

    it('renders a result whose task id is absent instead of taking the list down', async () => {
      // The producer's absence, not the type's: Task.id is declared as a required string, so a
      // result that omits the key is invisible to the compiler. Unfixed this threw while rendering
      // the row's "ID: …" line and took the results list with it.
      vi.mocked(api.searchTasks).mockResolvedValue([
        { title: 'Implement authentication', status: 'in_progress', priority: 'high' } as unknown as Task,
      ]);
      vi.mocked(api.listTasks).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      await userEvent.type(
        screen.getByPlaceholderText('Search tasks and subtasks by ID or name...'),
        'auth'
      );

      expect(await screen.findByText('Implement authentication')).toBeInTheDocument();
    });

    it('should search subtasks when typing', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([mockTasks[0]]);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(api.listTasks).toHaveBeenCalledWith({ git_branch_id: mockTaskTreeId });
        expect(api.listSubtasks).toHaveBeenCalledWith('task-1');
        expect(screen.getByText('Create login form')).toBeInTheDocument();
        expect(screen.getByText('Subtasks (1)')).toBeInTheDocument();
      });
    });

    it('should show "No results found" when search returns empty', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'nonexistent');

      await waitFor(() => {
        expect(screen.getByText('No results found for "nonexistent"')).toBeInTheDocument();
      });
    });

    it('should not search with empty query', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      // Type and then clear
      await userEvent.type(searchInput, 'test');
      await userEvent.clear(searchInput);

      await waitFor(() => {
        expect(screen.queryByText('No results found')).not.toBeInTheDocument();
        expect(screen.queryByText('Tasks')).not.toBeInTheDocument();
      });
    });

    it('should show loading state while searching', async () => {
      // Create a delayed promise
      let resolveSearch: any;
      const searchPromise = new Promise((resolve) => {
        resolveSearch = resolve;
      });

      (api.searchTasks as ReturnType<typeof vi.fn>).mockReturnValue(searchPromise);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'loading');

      await waitFor(() => {
        expect(screen.getByText('Searching...')).toBeInTheDocument();
      });

      // Resolve the promise
      resolveSearch([]);

      await waitFor(() => {
        expect(screen.queryByText('Searching...')).not.toBeInTheDocument();
      });
    });

    it('should handle search errors gracefully', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Search failed'));
      (api.listTasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('List failed'));

      const loggerSpy = vi.spyOn(logger, 'error').mockImplementation();

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'error');

      await waitFor(() => {
        expect(loggerSpy).toHaveBeenCalledWith(
          'Task search operation failed',
          expect.objectContaining({ error: expect.any(Error), query: 'error' })
        );
        expect(screen.getByText('No results found for "error"')).toBeInTheDocument();
      });

      loggerSpy.mockRestore();
    });
  });

  describe('Clear Search', () => {
    it('should show clear button when there is text', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      // Initially no clear button
      expect(screen.queryByRole('button', { name: '' })).not.toBeInTheDocument();

      await userEvent.type(searchInput, 'test');

      // Clear button should appear
      const clearButton = screen.getByRole('button');
      expect(clearButton.querySelector('.lucide-x')).toBeInTheDocument();
    });

    it('should clear search when clear button is clicked', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'test');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
      });

      const clearButton = screen.getByRole('button');
      fireEvent.click(clearButton);

      expect(searchInput).toHaveValue('');
      expect(screen.queryByText('Implement authentication')).not.toBeInTheDocument();
      expect(screen.queryByRole('button')).not.toBeInTheDocument(); // Clear button hidden
    });
  });

  describe('Task Selection', () => {
    beforeEach(async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    });

    it('should call onTaskSelect when task is clicked', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
      });

      const taskItem = screen.getByText('Implement authentication').closest('li');
      fireEvent.click(taskItem!);

      expect(mockOnTaskSelect).toHaveBeenCalledWith(mockTasks[0]);
      expect(searchInput).toHaveValue('');
      expect(screen.queryByText('Implement authentication')).not.toBeInTheDocument();
    });

    it('should display task details correctly', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('ID: task-1...')).toBeInTheDocument();
        expect(screen.getByText('in progress')).toBeInTheDocument();
        expect(screen.getByText('high')).toBeInTheDocument();
      });
    });
  });

  describe('Subtask Selection', () => {
    beforeEach(async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([mockTasks[0]]);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
    });

    it('should call onSubtaskSelect when subtask is clicked', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
      });

      const subtaskItem = screen.getByText('Create login form').closest('li');
      fireEvent.click(subtaskItem!);

      expect(mockOnSubtaskSelect).toHaveBeenCalledWith(mockSubtasks[0], mockTasks[0]);
      expect(searchInput).toHaveValue('');
      expect(screen.queryByText('Create login form')).not.toBeInTheDocument();
    });

    it('should display parent task information for subtasks', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
        expect(screen.getByText('Parent: Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('done')).toBeInTheDocument();
        expect(screen.getByText('medium')).toBeInTheDocument();
      });
    });

    it('should handle subtask loading errors', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load subtasks'));

      const loggerSpy = vi.spyOn(logger, 'error').mockImplementation();

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(loggerSpy).toHaveBeenCalledWith(
          'Failed to fetch subtasks for task',
          expect.objectContaining({ taskId: 'task-1', error: expect.any(Error) })
        );
      });

      loggerSpy.mockRestore();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should focus search input when Ctrl+K is pressed', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      // Blur the input first
      searchInput.blur();
      expect(document.activeElement).not.toBe(searchInput);

      // Press Ctrl+K
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });

      expect(document.activeElement).toBe(searchInput);
    });

    it('should focus search input when Cmd+K is pressed (Mac)', async () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      searchInput.blur();

      // Press Cmd+K
      fireEvent.keyDown(window, { key: 'k', metaKey: true });

      expect(document.activeElement).toBe(searchInput);
    });

    it('should clear search when Escape is pressed', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'test');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
      });

      // Press Escape
      fireEvent.keyDown(window, { key: 'Escape' });

      expect(searchInput).toHaveValue('');
      expect(screen.queryByText('Implement authentication')).not.toBeInTheDocument();
    });

    it('should not clear search with Escape when no results shown', () => {
      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');
      searchInput.focus();

      // Press Escape without search results
      fireEvent.keyDown(window, { key: 'Escape' });

      // Should not affect anything
      expect(document.activeElement).toBe(searchInput);
    });
  });

  describe('Debounced Search', () => {
    it('should search subtasks case-insensitively', async () => {
      const mixedCaseSubtasks = [
        { id: 'sub-1', title: 'CREATE LOGIN FORM', status: 'done', priority: 'medium', description: 'Design and implement login form' }
      ];

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([mockTasks[0]]);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mixedCaseSubtasks);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('CREATE LOGIN FORM')).toBeInTheDocument();
      });
    });

    it('should search by ID', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockImplementation((query: string) =>
        Promise.resolve(query === 'task-1' ? [mockTasks[0]] : [])
      );
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'task-1');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
      });

      await userEvent.clear(searchInput);
      await userEvent.type(searchInput, 'sub-1');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
      });
    });

    it('should search in descriptions', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'Design');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
      });
    });
  });

  describe('Results Display', () => {
    it('should display correct counts for tasks and subtasks', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([mockTasks[0]]);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'a'); // Will match both tasks and subtasks

      await waitFor(() => {
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
        expect(screen.getByText('Subtasks (2)')).toBeInTheDocument();
      });
    });

    it('should render results inside the search panel', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'test');

      await waitFor(() => {
        const resultsPanel = screen.getByText('Tasks (2)').closest('.rounded-3xl');
        expect(resultsPanel).toBeInTheDocument();
        expect(resultsPanel).toHaveClass('shadow-lg');
      });
    });

    it('should render all results without a fixed height cap', async () => {
      // Create many tasks to test that every result is rendered
      const manyTasks = Array.from({ length: 20 }, (_, i) => ({
        id: `task-${i}`,
        title: `Task ${i}`,
        status: 'todo',
        priority: 'medium'
      }));

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue(manyTasks);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'task');

      await waitFor(() => {
        const resultsPanel = screen.getByText('Tasks (20)').closest('.rounded-3xl');
        expect(resultsPanel).toBeInTheDocument();
        expect(resultsPanel).not.toHaveClass('max-h-96');
        expect(screen.getAllByText(/^Task \d+$/)).toHaveLength(20);
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle tasks without subtasks', async () => {
      const taskWithoutSubtasks = { ...mockTasks[1], subtasks: undefined };

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithoutSubtasks]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithoutSubtasks]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'fix');

      await waitFor(() => {
        expect(screen.getByText('Fix login bug')).toBeInTheDocument();
        expect(screen.queryByText(/^Subtasks \(/)).not.toBeInTheDocument();
      });
    });

    it('should handle empty subtask array', async () => {
      const taskWithEmptySubtasks = { ...mockTasks[0], subtasks: [] };

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithEmptySubtasks]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithEmptySubtasks]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.queryByText(/^Subtasks \(/)).not.toBeInTheDocument();
      });
    });

    it('should handle special characters in search', async () => {
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, '!@#$%^&*()');

      await waitFor(() => {
        expect(screen.getByText('No results found for "!@#$%^&*()"')).toBeInTheDocument();
      });
    });

    it('should handle very long search queries', async () => {
      const longQuery = 'a'.repeat(100);

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name...');

      await userEvent.type(searchInput, longQuery);

      await waitFor(() => {
        expect(api.searchTasks).toHaveBeenCalledWith(longQuery, { git_branch_id: mockTaskTreeId });
      });
    });
  });

  describe('Component Cleanup', () => {
    it('should remove keyboard event listeners on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    });
  });
});
