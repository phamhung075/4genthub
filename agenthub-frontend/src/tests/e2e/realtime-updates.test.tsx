import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import LazyTaskList from '../../components/LazyTaskList';
import { changePoolService, ChangeNotification } from '../../services/changePoolService';
import * as api from '../../api';

// Mock API
vi.mock('../../api', () => ({
  listTasks: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
  listAgents: vi.fn(),
  getAvailableAgents: vi.fn()
}));

// Mock WebSocket
vi.mock('../../hooks/useWebSocketV2', () => ({
  useTaskWebSocket: vi.fn(() => ({
    isConnected: true,
    connectionStatus: 'connected'
  }))
}));

// Mock Auth
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 'e2e-user' },
    tokens: { access_token: 'e2e-token' }
  }))
}));

// Mock Redux
vi.mock('../../store/hooks', () => ({
  useAppSelector: vi.fn(() => null)
}));

// Mock toast
vi.mock('../../components/ui/toast', () => ({
  useErrorToast: vi.fn(() => vi.fn())
}));

// Mock components to simplify E2E testing
vi.mock('../../components/TaskDetailsDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/TaskEditDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/AgentAssignmentDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/TaskContextDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/DeleteConfirmDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/AgentInfoDialog', () => ({
  __esModule: true,
  default: () => null
}));

vi.mock('../../components/TaskSearch', () => ({
  __esModule: true,
  default: () => <div data-testid="task-search">Search</div>
}));

describe('End-to-End Real-time Updates', () => {
  const mockProjectId = 'e2e-project';
  const mockTaskTreeId = 'e2e-branch';

  const initialTasks = [
    {
      id: 'e2e-task-1',
      title: 'E2E Task 1',
      status: 'todo',
      priority: 'high',
      subtasks: [],
      assignees: ['agent-1'],
      dependencies: [],
      context_id: 'ctx-1',
      created_at: '2024-01-01T10:00:00Z'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    changePoolService.clearAllSubscriptions();

    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024
    });
  });

  afterEach(() => {
    changePoolService.clearAllSubscriptions();
  });

  describe('Complete Real-time Flow', () => {
    it('should handle full create → update → delete flow without page refresh', async () => {
      // Setup initial API response
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={vi.fn()}
        />
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('E2E Task 1')).toBeInTheDocument();
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument();
      });

      // STEP 1: CREATE - Simulate backend creating a new task via WebSocket
      const createNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'e2e-task-2',
        eventType: 'created',
        userId: 'e2e-user',
        data: {
          id: 'e2e-task-2',
          title: 'Real-time Created Task',
          status: 'todo',
          priority: 'medium',
          subtasks: [],
          assignees: ['real-time-agent'],
          dependencies: [],
          context_id: 'ctx-2',
          created_at: new Date().toISOString()
        },
        metadata: {
          git_branch_id: mockTaskTreeId,
          project_id: mockProjectId
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        changePoolService.processChange(createNotification);
      });

      // Task should appear immediately
      await waitFor(() => {
        expect(screen.getByText('Real-time Created Task')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
      });

      // STEP 2: UPDATE - Simulate backend updating the task via WebSocket
      const updateNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'e2e-task-2',
        eventType: 'updated',
        userId: 'e2e-user',
        data: {
          id: 'e2e-task-2',
          title: 'Real-time Updated Task',
          status: 'in_progress',
          priority: 'critical',
          subtasks: [],
          assignees: ['real-time-agent'],
          dependencies: [],
          context_id: 'ctx-2'
        },
        metadata: {
          git_branch_id: mockTaskTreeId,
          project_id: mockProjectId
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        changePoolService.processChange(updateNotification);
      });

      // Task should update immediately
      await waitFor(() => {
        expect(screen.getByText('Real-time Updated Task')).toBeInTheDocument();
        expect(screen.queryByText('Real-time Created Task')).not.toBeInTheDocument();
        expect(screen.getByText('in_progress')).toBeInTheDocument();
        expect(screen.getByText('critical')).toBeInTheDocument();
        expect(screen.getByText('Tasks (2)')).toBeInTheDocument(); // Count stays same
      });

      // STEP 3: DELETE - Simulate backend deleting the task via WebSocket
      const deleteNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'e2e-task-2',
        eventType: 'deleted',
        userId: 'e2e-user',
        metadata: {
          git_branch_id: mockTaskTreeId,
          project_id: mockProjectId
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        changePoolService.processChange(deleteNotification);
      });

      // Task should disappear immediately
      await waitFor(() => {
        expect(screen.queryByText('Real-time Updated Task')).not.toBeInTheDocument();
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument(); // Count decreases
      });

      // Original task should still be there
      expect(screen.getByText('E2E Task 1')).toBeInTheDocument();

      // CRITICAL: No additional API calls should have been made after initial load
      expect(api.listTasks).toHaveBeenCalledTimes(1);
    });

    it('should handle concurrent real-time updates correctly', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument();
      });

      // Simulate rapid concurrent updates
      const updates = [
        {
          entityType: 'task',
          entityId: 'concurrent-1',
          eventType: 'created',
          data: {
            id: 'concurrent-1',
            title: 'Concurrent Task 1',
            status: 'todo',
            priority: 'high',
            subtasks: [],
            assignees: [],
            dependencies: [],
            created_at: new Date().toISOString()
          }
        },
        {
          entityType: 'task',
          entityId: 'concurrent-2',
          eventType: 'created',
          data: {
            id: 'concurrent-2',
            title: 'Concurrent Task 2',
            status: 'todo',
            priority: 'low',
            subtasks: [],
            assignees: [],
            dependencies: [],
            created_at: new Date().toISOString()
          }
        },
        {
          entityType: 'task',
          entityId: 'e2e-task-1',
          eventType: 'updated',
          data: {
            id: 'e2e-task-1',
            title: 'Updated E2E Task 1',
            status: 'done',
            priority: 'high',
            subtasks: [],
            assignees: ['agent-1'],
            dependencies: []
          }
        }
      ];

      // Send all updates rapidly
      act(() => {
        updates.forEach((update) => {
          const notification: ChangeNotification = {
            ...update,
            userId: 'e2e-user',
            metadata: { git_branch_id: mockTaskTreeId },
            timestamp: new Date().toISOString()
          } as ChangeNotification;

          changePoolService.processChange(notification);
        });
      });

      // All updates should be reflected
      await waitFor(() => {
        expect(screen.getByText('Concurrent Task 1')).toBeInTheDocument();
        expect(screen.getByText('Concurrent Task 2')).toBeInTheDocument();
        expect(screen.getByText('Updated E2E Task 1')).toBeInTheDocument();
        expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
        expect(screen.getByText('done')).toBeInTheDocument(); // Updated status
      });
    });

    it('should maintain UI consistency during rapid updates', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
      });

      // Create, update, and delete the same task rapidly
      const taskId = 'rapid-task';

      // CREATE
      act(() => {
        changePoolService.processChange({
          entityType: 'task',
          entityId: taskId,
          eventType: 'created',
          userId: 'e2e-user',
          data: {
            id: taskId,
            title: 'Rapid Task',
            status: 'todo',
            priority: 'medium',
            subtasks: [],
            assignees: [],
            dependencies: [],
            created_at: new Date().toISOString()
          },
          metadata: { git_branch_id: mockTaskTreeId },
          timestamp: new Date().toISOString()
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Rapid Task')).toBeInTheDocument();
        expect(screen.getByText('Tasks (1)')).toBeInTheDocument();
      });

      // UPDATE
      act(() => {
        changePoolService.processChange({
          entityType: 'task',
          entityId: taskId,
          eventType: 'updated',
          userId: 'e2e-user',
          data: {
            id: taskId,
            title: 'Rapid Task Updated',
            status: 'in_progress',
            priority: 'high',
            subtasks: [],
            assignees: [],
            dependencies: []
          },
          metadata: { git_branch_id: mockTaskTreeId },
          timestamp: new Date().toISOString()
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Rapid Task Updated')).toBeInTheDocument();
        expect(screen.getByText('in_progress')).toBeInTheDocument();
      });

      // DELETE
      act(() => {
        changePoolService.processChange({
          entityType: 'task',
          entityId: taskId,
          eventType: 'deleted',
          userId: 'e2e-user',
          metadata: { git_branch_id: mockTaskTreeId },
          timestamp: new Date().toISOString()
        });
      });

      await waitFor(() => {
        expect(screen.queryByText('Rapid Task Updated')).not.toBeInTheDocument();
        expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
      });

      // UI should be in clean state
      expect(screen.queryByText('todo')).not.toBeInTheDocument();
      expect(screen.queryByText('in_progress')).not.toBeInTheDocument();
    });
  });

  describe('Network and Error Scenarios', () => {
    it('should handle WebSocket reconnection gracefully', async () => {
      (api.listTasks as ReturnType<typeof vi.fn>).mockResolvedValue(initialTasks);

      // Mock WebSocket disconnection/reconnection
      const mockUseTaskWebSocket = vi.mocked(require('../../hooks/useWebSocketV2').useTaskWebSocket);

      mockUseTaskWebSocket.mockReturnValue({
        isConnected: false,
        connectionStatus: 'disconnected'
      });

      const { rerender } = render(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Offline')).toBeInTheDocument();
      });

      // Simulate reconnection
      mockUseTaskWebSocket.mockReturnValue({
        isConnected: true,
        connectionStatus: 'connected'
      });

      rerender(
        <LazyTaskList
          projectId={mockProjectId}
          taskTreeId={mockTaskTreeId}
          onTasksChanged={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Live')).toBeInTheDocument();
      });

      // Real-time updates should work after reconnection
      act(() => {
        changePoolService.processChange({
          entityType: 'task',
          entityId: 'reconnect-task',
          eventType: 'created',
          userId: 'e2e-user',
          data: {
            id: 'reconnect-task',
            title: 'Post-Reconnect Task',
            status: 'todo',
            priority: 'medium',
            subtasks: [],
            assignees: [],
            dependencies: [],
            created_at: new Date().toISOString()
          },
          metadata: { git_branch_id: mockTaskTreeId },
          timestamp: new Date().toISOString()
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Post-Reconnect Task')).toBeInTheDocument();
      });
    });
  });
});