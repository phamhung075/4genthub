import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { TaskSearch } from '../../components/TaskSearch';
import * as api from '../../api';

// Mock the api module
vi.mock('../../api');

// Mock debounce to execute immediately in tests
vi.mock('../../lib/utils', () => ({
  ...vi.importActual('../../lib/utils'),
  debounce: (fn: any) => fn
}));

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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(api.searchTasks).toHaveBeenCalledWith('auth', mockTaskTreeId);
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'error');

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Search error:', expect.any(Error));
        expect(screen.getByText('No results found for "error"')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
      });

      const taskItem = screen.getByText('Implement authentication').closest('.hover\\:bg-gray-100');
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('ID: task-1')).toBeInTheDocument();
        expect(screen.getByText('in_progress')).toBeInTheDocument();
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
      });

      const subtaskItem = screen.getByText('Create login form').closest('.hover\\:bg-gray-100');
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('Create login form')).toBeInTheDocument();
        expect(screen.getByText('Parent: Implement authentication')).toBeInTheDocument();
        expect(screen.getByText('ID: sub-1')).toBeInTheDocument();
        expect(screen.getByText('done')).toBeInTheDocument();
        expect(screen.getByText('medium')).toBeInTheDocument();
      });
    });

    it('should handle subtask loading errors', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load subtasks'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Error fetching subtasks for task task-1:', 
          expect.any(Error)
        );
      });

      consoleSpy.mockRestore();
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      searchInput.focus();

      // Press Escape without search results
      fireEvent.keyDown(window, { key: 'Escape' });

      // Should not affect anything
      expect(document.activeElement).toBe(searchInput);
    });
  });

  describe('Debounced Search', () => {
    it('should search case-insensitively', async () => {
      const tasksWithMixedCase = [
        { ...mockTasks[0], title: 'IMPLEMENT AUTHENTICATION' },
        { ...mockTasks[1], title: 'fix Login BUG' }
      ];

      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(tasksWithMixedCase);
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockImplementation(() => Promise.resolve([]));

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'login');

      await waitFor(() => {
        expect(screen.getByText('fix Login BUG')).toBeInTheDocument();
      });
    });

    it('should search by ID', async () => {
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'a'); // Will match both tasks and subtasks

      await waitFor(() => {
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
        expect(screen.getByText('Subtasks (2)')).toBeInTheDocument();
      });
    });

    it('should maintain result panel position', async () => {
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'test');

      await waitFor(() => {
        const resultsCard = screen.getByText('Tasks (2)').closest('.card');
        expect(resultsCard).toHaveClass('absolute');
        expect(resultsCard).toHaveClass('z-50');
        expect(resultsCard).toHaveClass('shadow-lg');
      });
    });

    it('should limit result panel height with scroll', async () => {
      // Create many tasks to test scrolling
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'task');

      await waitFor(() => {
        const resultsCard = screen.getByText('Tasks (20)').closest('.card');
        expect(resultsCard).toHaveClass('max-h-96');
        expect(resultsCard).toHaveClass('overflow-y-auto');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle tasks without subtasks', async () => {
      const taskWithoutSubtasks = { ...mockTasks[1], subtasks: undefined };
      
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithoutSubtasks]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'fix');

      await waitFor(() => {
        expect(screen.getByText('Fix login bug')).toBeInTheDocument();
        expect(screen.queryByText('Subtasks')).not.toBeInTheDocument();
      });
    });

    it('should handle empty subtask array', async () => {
      const taskWithEmptySubtasks = { ...mockTasks[0], subtasks: [] };
      
      (api.searchTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([taskWithEmptySubtasks]);

      render(
        <TaskSearch
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTaskSelect={mockOnTaskSelect}
          onSubtaskSelect={mockOnSubtaskSelect}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, 'auth');

      await waitFor(() => {
        expect(screen.getByText('Implement authentication')).toBeInTheDocument();
        expect(screen.queryByText('Subtasks')).not.toBeInTheDocument();
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
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

      const searchInput = screen.getByPlaceholderText('Search tasks and subtasks by ID or name... (Ctrl+K)');
      
      await userEvent.type(searchInput, longQuery);

      await waitFor(() => {
        expect(api.searchTasks).toHaveBeenCalledWith(longQuery, mockTaskTreeId);
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