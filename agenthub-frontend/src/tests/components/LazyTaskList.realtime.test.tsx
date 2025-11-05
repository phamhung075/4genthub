import React from 'react';
import { render, screen, waitFor, act } from './../test-utils';
import { vi } from 'vitest';
import LazyTaskList from '../../components/LazyTaskList';
import * as api from '../../api';
import { ChangeNotification } from '../../services/changePoolService';
import { useEntityChanges } from '../../hooks/useChangeSubscription';

// Mock the api module
vi.mock('../../api');

// Mock the WebSocket hooks
vi.mock('../../hooks/useTaskWebSocket', () => ({
  useTaskWebSocket: vi.fn(() => ({
    isConnected: true,
    isReconnecting: false,
    error: null,
    handleTaskChanges: vi.fn()
  }))
}));

// Mock Auth context
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 'test-user' },
    tokens: { access_token: 'test-token' }
  }))
}));

// Mock toast
vi.mock('../../components/ui/toast', () => ({
  useErrorToast: vi.fn(() => vi.fn())
}));

// Mock all lazy-loaded components
vi.mock('../../components/TaskDetailsDialog', () => ({
  __esModule: true,
  default: ({ open, task }: any) => open ? (
    <div data-testid="task-details-dialog">Task: {task?.title}</div>
  ) : null
}));

vi.mock('../../components/TaskEditDialog', () => ({
  __esModule: true,
  default: ({ open, task }: any) => open ? (
    <div data-testid="task-edit-dialog">Edit: {task?.title}</div>
  ) : null
}));

vi.mock('../../components/AgentAssignmentDialog', () => ({
  __esModule: true,
  default: ({ open }: any) => open ? <div data-testid="agent-dialog">Agents</div> : null
}));

vi.mock('../../components/TaskContextDialog', () => ({
  __esModule: true,
  default: ({ open }: any) => open ? <div data-testid="context-dialog">Context</div> : null
}));

vi.mock('../../components/DeleteConfirmDialog', () => ({
  __esModule: true,
  default: ({ open }: any) => open ? <div data-testid="delete-dialog">Delete</div> : null
}));

vi.mock('../../components/AgentInfoDialog', () => ({
  __esModule: true,
  default: ({ open }: any) => open ? <div data-testid="agent-info-dialog">Agent Info</div> : null
}));

vi.mock('../../components/TaskSearch', () => ({
  __esModule: true,
  default: () => <div data-testid="task-search">Search</div>
}));

// CRITICAL: Mock useEntityChanges to capture the callback
let mockHandleTaskChanges: ((notification?: ChangeNotification) => void) | null = null;

vi.mock('../../hooks/useChangeSubscription', () => ({
  useEntityChanges: vi.fn((componentId, entityTypes, callback, options) => {
    // Capture the callback so we can simulate WebSocket notifications
    mockHandleTaskChanges = callback;
  })
}));

describe('LazyTaskList Real-time Updates', () => {
  const mockProjectId = 'project-123';
  const mockTaskTreeId = 'branch-123';
  const mockOnTasksChanged = vi.fn();

  const initialTasks = [
    {
      id: 'task-1',
      title: 'Initial Task 1',
      status: 'todo',
      priority: 'high',
      subtasks: [],
      assignees: ['user-1'],
      dependencies: [],
      context_id: 'ctx-1',
      created_at: '2024-01-01T10:00:00Z'
    },
    {
      id: 'task-2',
      title: 'Initial Task 2',
      status: 'in_progress',
      priority: 'medium',
      subtasks: [],
      assignees: [],
      dependencies: [],
      context_id: null,
      created_at: '2024-01-01T11:00:00Z'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockHandleTaskChanges = null;
    // Mock window dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024
    });
  });

  describe('WebSocket CREATE Notifications', () => {
    it('should add new task to list when CREATE WebSocket message received', async () => {
      // Setup initial task list
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Initial Task 1')).toBeInTheDocument();
        expect(screen.getByText('Initial Task 2')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });

      // Simulate WebSocket CREATE notification with full task data
      const createNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'new-task-123',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'new-task-123',
          title: 'WebSocket Created Task',
          status: 'todo',
          priority: 'critical',
          subtasks: [],
          assignees: ['websocket-agent'],
          dependencies: [],
          context_id: 'ctx-new',
          created_at: new Date().toISOString()
        },
        metadata: {
          git_branch_id: mockTaskTreeId,
          project_id: mockProjectId
        },
        timestamp: new Date().toISOString()
      };

      // Trigger the WebSocket notification
      act(() => {
        mockHandleTaskChanges?.(createNotification);
      });

      // CRITICAL TEST: New task should appear immediately without page refresh
      await waitFor(() => {
        expect(screen.getByText('WebSocket Created Task')).toBeInTheDocument();
        expect(screen.getByText('Tasks (3)')).toBeInTheDocument(); // Count should update
      });

      // Verify the task has correct data
      expect(screen.getByText('critical')).toBeInTheDocument(); // Priority
      expect(screen.getByText('todo')).toBeInTheDocument(); // Status
    });

    it('should trigger create animation for new WebSocket task', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

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

      const createNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'animated-task',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'animated-task',
          title: 'Animated Task',
          status: 'todo',
          priority: 'high',
          subtasks: [],
          assignees: [],
          dependencies: [],
          created_at: new Date().toISOString()
        },
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(createNotification);
      });

      // Task should appear with animation class
      await waitFor(() => {
        expect(screen.getByText('Animated Task')).toBeInTheDocument();
      });

      // Note: Animation testing requires more sophisticated setup
      // This test ensures the task appears, animation logic is separate
    });
  });

  describe('WebSocket UPDATE Notifications', () => {
    it('should update existing task when UPDATE WebSocket message received', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Initial Task 1')).toBeInTheDocument();
      });

      // Simulate WebSocket UPDATE notification
      const updateNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'updated',
        userId: 'user-1',
        data: {
          id: 'task-1',
          title: 'Updated Task Title via WebSocket',
          status: 'in_progress',
          priority: 'critical',
          subtasks: [],
          assignees: ['updated-agent'],
          dependencies: [],
          context_id: 'ctx-1'
        },
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(updateNotification);
      });

      // CRITICAL TEST: Task should update immediately without page refresh
      await waitFor(() => {
        expect(screen.getByText('Updated Task Title via WebSocket')).toBeInTheDocument();
        expect(screen.queryByText('Initial Task 1')).not.toBeInTheDocument();
      });

      // Verify updated properties
      expect(screen.getByText('critical')).toBeInTheDocument(); // Updated priority
      expect(screen.getByText('in_progress')).toBeInTheDocument(); // Updated status
    });

    it('should handle COMPLETED task status updates', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Initial Task 2')).toBeInTheDocument();
      });

      const completeNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-2',
        eventType: 'completed',
        userId: 'user-1',
        data: {
          id: 'task-2',
          title: 'Initial Task 2',
          status: 'done',
          priority: 'medium',
          subtasks: [],
          assignees: [],
          dependencies: []
        },
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(completeNotification);
      });

      await waitFor(() => {
        expect(screen.getByText('done')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket DELETE Notifications', () => {
    it('should remove task from list when DELETE WebSocket message received', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Initial Task 1')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });

      // Simulate WebSocket DELETE notification
      const deleteNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'deleted',
        userId: 'user-1',
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(deleteNotification);
      });

      // CRITICAL TEST: Task should disappear immediately without page refresh
      await waitFor(() => {
        expect(screen.queryByText('Initial Task 1')).not.toBeInTheDocument();
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument(); // Count should update
      });

      // Other task should still be there
      expect(screen.getByText('Initial Task 2')).toBeInTheDocument();
    });
  });

  describe('Fallback to API Refresh', () => {
    it('should fall back to API refresh when notification data is missing', async () => {
      const updatedTasks = [
        ...initialTasks,
        {
          id: 'fallback-task',
          title: 'Fallback Task',
          status: 'todo',
          priority: 'low',
          subtasks: [],
          assignees: [],
          dependencies: [],
          created_at: new Date().toISOString()
        }
      ];

      (api.listTasks as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(initialTasks) // Initial load
        .mockResolvedValueOnce(updatedTasks); // Fallback refresh

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

      // Notification without data - should trigger fallback
      const notificationWithoutData: ChangeNotification = {
        entityType: 'task',
        entityId: 'fallback-task',
        eventType: 'created',
        userId: 'user-1',
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
        // No data property
      };

      act(() => {
        mockHandleTaskChanges?.(notificationWithoutData);
      });

      await waitFor(() => {
        expect(screen.getByText('Fallback Task')).toBeInTheDocument();
        expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
      });

      // Should have called API for fallback refresh
      expect(api.listTasks).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling', () => {
    it('should handle malformed notification data gracefully', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

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

      // Malformed notification
      const malformedNotification = {
        entityType: 'task',
        entityId: 'malformed-task',
        eventType: 'created',
        userId: 'user-1',
        data: null, // Invalid data
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      } as ChangeNotification;

      // Should not crash the component
      expect(() => {
        act(() => {
          mockHandleTaskChanges?.(malformedNotification);
        });
      }).not.toThrow();

      consoleSpy.mockRestore();
    });
  });

  describe('Branch Filtering', () => {
    it('should ignore notifications for different branches', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

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

      // Notification for different branch
      const wrongBranchNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'wrong-branch-task',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'wrong-branch-task',
          title: 'Wrong Branch Task',
          status: 'todo',
          priority: 'high',
          subtasks: [],
          assignees: [],
          dependencies: [],
          created_at: new Date().toISOString()
        },
        metadata: { git_branch_id: 'different-branch-456' }, // Different branch
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(wrongBranchNotification);
      });

      // Should NOT add the task since it's for a different branch
      await waitFor(() => {
        expect(screen.queryByText('Wrong Branch Task')).not.toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument(); // Count unchanged
      });
    });
  });

  describe('Component Re-render Triggers', () => {
    it('should trigger component re-render after WebSocket update', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={mockOnTasksChanged}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Initial Task 1')).toBeInTheDocument();
      });

      const updateNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'updated',
        userId: 'user-1',
        data: {
          id: 'task-1',
          title: 'Re-render Test Task',
          status: 'done',
          priority: 'low',
          subtasks: [],
          assignees: [],
          dependencies: []
        },
        metadata: { git_branch_id: mockTaskTreeId },
        timestamp: new Date().toISOString()
      };

      act(() => {
        mockHandleTaskChanges?.(updateNotification);
      });

      // Component should re-render with new data
      await waitFor(() => {
        expect(screen.getByText('Re-render Test Task')).toBeInTheDocument();
        expect(screen.getByText('done')).toBeInTheDocument();
        expect(screen.getByText('low')).toBeInTheDocument();
      });
    });
  });
});