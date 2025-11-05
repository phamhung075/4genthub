import { fireEvent, render, screen, waitFor, act } from './../test-utils';
import React from 'react';
import { vi } from 'vitest';
import * as api from '../../api';
import { Task } from '../../api';
import TaskDetailsDialog from '../../components/TaskDetailsDialog';
import { useTaskWebSocket } from '../../hooks/useTaskWebSocket';

// Mock the api module
vi.mock('../../api', () => ({
  getTask: vi.fn(),
  getTaskContext: vi.fn(),
  getCurrentUserId: vi.fn(() => 'mock-user-id')
}));

// Mock the context helpers
vi.mock('../../utils/contextHelpers', () => ({
  formatContextDisplay: vi.fn((contextData) => ({
    hasInfo: !!contextData,
    completionSummary: contextData?.completion_summary || null,
    completionPercentage: contextData?.completion_percentage || null,
    taskStatus: contextData?.status || null,
    testingNotes: contextData?.testing_notes || [],
    isLegacy: false
  }))
}));

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn(() => 'mock-token')
  }
}));

// Mock the WebSocket hook with controllable behavior
let mockOnTaskUpdate: ((notification: any) => boolean) | null = null;
vi.mock('../../hooks/useTaskWebSocket', () => ({
  useTaskWebSocket: vi.fn((config) => {
    mockOnTaskUpdate = config.onTaskUpdate;
    return {
      isConnected: true,
      isReconnecting: false,
      error: null,
      handleTaskChanges: vi.fn()
    };
  })
}));

// Mock ClickableAssignees component
vi.mock('../../components/ClickableAssignees', () => ({
  __esModule: true,
  default: ({ assignees, onAgentClick, variant }: any) => (
    <div data-testid="clickable-assignees">
      {assignees.map((assignee: string, index: number) => (
        <button
          key={index}
          onClick={() => onAgentClick(assignee, {})}
          className={`assignee-${variant}`}
        >
          {assignee}
        </button>
      ))}
    </div>
  )
}));

// Mock other UI components
vi.mock('../../components/ProgressHistoryTimeline', () => ({
  ProgressHistoryTimeline: ({ progressHistory, progressCount, variant, className }: any) => (
    <div data-testid="progress-history-timeline" className={className}>
      Progress History Timeline Mock
    </div>
  )
}));

vi.mock('../../components/ui/CopyableId', () => ({
  CopyableId: ({ id, variant, size, abbreviated, showCopyButton, className }: any) => (
    <span data-testid="copyable-id" className={className}>
      {abbreviated && id.length > 8 ? id.substring(0, 8) : id}
    </span>
  )
}));

vi.mock('../../components/ui/RawJSONDisplay', () => ({
  __esModule: true,
  default: ({ jsonData, title, fileName }: any) => (
    <div data-testid="raw-json-display">
      <pre>{JSON.stringify(jsonData, null, 2)}</pre>
    </div>
  )
}));

vi.mock('../../components/ui/EnhancedJSONViewer', () => ({
  EnhancedJSONViewer: ({ data, defaultExpanded, maxHeight }: any) => (
    <div data-testid="enhanced-json-viewer" className={maxHeight}>
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <span>{key}</span>: <span>{String(value)}</span>
        </div>
      ))}
    </div>
  )
}));

describe('TaskDetailsDialog WebSocket Integration', () => {
  const mockTask: Task = {
    id: 'task-123',
    title: 'Test Task',
    description: 'Test task description',
    status: 'in_progress',
    priority: 'high',
    git_branch_id: 'branch-123',
    project_id: 'project-123',
    context_id: 'context-123',
    created_at: '2025-08-27T10:00:00Z',
    updated_at: '2025-08-27T11:00:00Z',
    assignees: ['user1'],
    labels: [],
    dependencies: [],
    subtasks: [],
    progress_history: [],
    progress_count: 0
  };

  const mockTaskContext = {
    data: {
      resolved_context: {
        task_data: { key: 'value' }
      }
    }
  };

  const mockOnClose = vi.fn();
  const mockOnAgentClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnTaskUpdate = null;
  });

  describe('WebSocket Updates', () => {
    it('should update task when WebSocket notification is received', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Simulate WebSocket notification
      const updatedTaskData = {
        ...mockTask,
        title: 'Updated Task Title',
        status: 'done'
      };

      act(() => {
        if (mockOnTaskUpdate) {
          const result = mockOnTaskUpdate({
            entityId: 'task-123',
            eventType: 'updated',
            data: updatedTaskData
          });
          expect(result).toBe(true); // Should be handled
        }
      });

      // Check that UI updates with new data
      await waitFor(() => {
        expect(screen.getByText('Updated Task Title')).toBeInTheDocument();
        expect(screen.getByText(/Status: done/i)).toBeInTheDocument();
      });

      // Should show "Updated" badge briefly
      expect(screen.getByText('Updated')).toBeInTheDocument();
    });

    it('should trigger API fallback when notification lacks full data', async () => {
      const updatedTask = { ...mockTask, title: 'API Fetched Title' };
      (api.getTask as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(mockTask)
        .mockResolvedValueOnce(updatedTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Simulate WebSocket notification requiring API fallback
      act(() => {
        if (mockOnTaskUpdate) {
          const result = mockOnTaskUpdate({
            entityId: 'task-123',
            eventType: 'api_fallback_needed'
          });
          expect(result).toBe(true); // Should be handled
        }
      });

      // Should trigger API call
      await waitFor(() => {
        expect(api.getTask).toHaveBeenCalledTimes(2); // Initial + fallback
        expect(api.getTask).toHaveBeenLastCalledWith('task-123');
      });

      // Should update UI with API data
      await waitFor(() => {
        expect(screen.getByText('API Fetched Title')).toBeInTheDocument();
      });
    });

    it('should not update if notification is for different task', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Simulate WebSocket notification for different task
      act(() => {
        if (mockOnTaskUpdate) {
          const result = mockOnTaskUpdate({
            entityId: 'different-task-id',
            eventType: 'updated',
            data: { title: 'Different Task' }
          });
          expect(result).toBe(false); // Should not be handled
        }
      });

      // UI should not change
      expect(screen.getByText('Test Task')).toBeInTheDocument();
      expect(screen.queryByText('Different Task')).not.toBeInTheDocument();
    });

    it('should refetch context when task is updated via WebSocket', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(mockTaskContext)
        .mockResolvedValueOnce({
          data: {
            resolved_context: {
              task_data: { key: 'updated value' }
            }
          }
        });

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Simulate WebSocket notification
      act(() => {
        if (mockOnTaskUpdate) {
          mockOnTaskUpdate({
            entityId: 'task-123',
            eventType: 'updated',
            data: { ...mockTask, status: 'done' }
          });
        }
      });

      // Should refetch context
      await waitFor(() => {
        expect(api.getTaskContext).toHaveBeenCalledTimes(2); // Initial + after update
        expect(api.getTaskContext).toHaveBeenLastCalledWith('task-123');
      });
    });

    it('should preserve existing data when WebSocket update is partial', async () => {
      const taskWithContext = {
        ...mockTask,
        context_data: {
          existing: 'data',
          nested: { value: 'original' }
        }
      };

      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(taskWithContext);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={taskWithContext}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Simulate partial WebSocket update
      act(() => {
        if (mockOnTaskUpdate) {
          mockOnTaskUpdate({
            entityId: 'task-123',
            eventType: 'updated',
            data: {
              ...taskWithContext,
              title: 'Partially Updated',
              // context_data is not included in update
            }
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('Partially Updated')).toBeInTheDocument();
      });

      // Context data should be preserved
      // This would be visible in the actual component's state
      // but we can verify it wasn't overwritten by checking the mock wasn't called again
      expect(api.getTask).toHaveBeenCalledTimes(1); // Only initial call
    });
  });

  describe('WebSocket Connection Parameters', () => {
    it('should pass correct parameters to useTaskWebSocket hook', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(useTaskWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({
            userId: 'mock-user-id',
            token: 'mock-token',
            taskTreeId: 'branch-123',
            projectId: 'project-123',
            onTaskUpdate: expect.any(Function)
          })
        );
      });
    });

    it('should handle missing task data gracefully', () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={null}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      // Should still render but with empty parameters
      expect(useTaskWebSocket).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 'mock-user-id',
          token: 'mock-token',
          taskTreeId: '',
          projectId: '',
          onTaskUpdate: expect.any(Function)
        })
      );
    });
  });

  describe('Visual Feedback', () => {
    it('should show and hide "Updated" badge after WebSocket update', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Initially no "Updated" badge
      expect(screen.queryByText('Updated')).not.toBeInTheDocument();

      // Trigger WebSocket update
      act(() => {
        if (mockOnTaskUpdate) {
          mockOnTaskUpdate({
            entityId: 'task-123',
            eventType: 'updated',
            data: { ...mockTask, status: 'done' }
          });
        }
      });

      // Should show "Updated" badge
      await waitFor(() => {
        expect(screen.getByText('Updated')).toBeInTheDocument();
      });

      // Wait for badge to disappear (2 seconds in component)
      await waitFor(
        () => {
          expect(screen.queryByText('Updated')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });
});