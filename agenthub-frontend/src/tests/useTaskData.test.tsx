/**
 * Tests for useTaskData hook (React Query version)
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTaskData } from '../hooks/useTaskData';
import { listTasks } from '../api';
import { getFullTask } from '../api-lazy';
import { createTestQueryClient } from './query-utils';

// Mock the API functions
vi.mock('../api', () => ({
  listTasks: vi.fn(),
}));

vi.mock('../api-lazy', () => ({
  getFullTask: vi.fn(),
}));

describe('useTaskData (React Query)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  const mockTasks = [
    {
      id: 'task-1',
      title: 'Task 1',
      status: 'todo',
      priority: 'high',
      subtask_count: 3,
      assignees: ['user-1'],
      dependencies: [],
      created_at: '2024-01-01',
    },
    {
      id: 'task-2',
      title: 'Task 2',
      status: 'in_progress',
      priority: 'medium',
      subtask_count: 0,
      assignees: [],
      dependencies: ['task-1'],
      created_at: '2024-01-02',
    },
  ];

  it('should load task summaries successfully', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.taskSummaries).toHaveLength(2);
    expect(result.current.totalTasks).toBe(2);
    expect(result.current.error).toBeNull();
  });

  it('should filter out subtasks from top-level list', async () => {
    const tasksWithSubtask = [
      ...mockTasks,
      {
        id: 'subtask-1',
        title: 'Subtask 1',
        parent_task_id: 'task-1',
        status: 'todo',
        priority: 'low',
        subtask_count: 0,
        assignees: [],
        dependencies: [],
        created_at: '2024-01-03',
      },
    ];

    vi.mocked(listTasks).mockResolvedValue(tasksWithSubtask);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Should only have 2 top-level tasks, subtask excluded
    expect(result.current.taskSummaries).toHaveLength(2);
    expect(result.current.taskSummaries.every(t => !('parent_task_id' in t))).toBe(true);
  });

  it('should load full task on demand', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);

    const fullTask = {
      ...mockTasks[0],
      description: 'Full task description',
      subtasks: [],
    };

    vi.mocked(getFullTask).mockResolvedValue(fullTask);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const loaded = await result.current.loadFullTask('task-1');

    expect(loaded).toEqual(fullTask);
    expect(getFullTask).toHaveBeenCalledWith('task-1');
  });

  it('should update task from WebSocket data', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const updatedTask = { ...mockTasks[0], status: 'done', subtask_count: 5 };
    result.current.updateTaskFromData(updatedTask);

    await waitFor(() => {
      const task = result.current.taskSummaries.find(t => t.id === 'task-1');
      expect(task?.status).toBe('done');
      expect(task?.subtask_count).toBe(5);
    });
  });

  it('should add new task via WebSocket', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.taskSummaries).toHaveLength(2);

    const newTask = {
      id: 'task-3',
      title: 'New Task',
      status: 'todo',
      priority: 'low',
      subtask_count: 0,
      assignees: [],
      dependencies: [],
      created_at: '2024-01-03',
    };

    result.current.addNewTask(newTask);

    await waitFor(() => {
      expect(result.current.taskSummaries).toHaveLength(3);
      expect(result.current.taskSummaries[0].id).toBe('task-3');
    });
  });

  it('should remove task', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.taskSummaries).toHaveLength(2);

    result.current.removeTask('task-1');

    await waitFor(() => {
      expect(result.current.taskSummaries).toHaveLength(1);
      expect(result.current.taskSummaries[0].id).toBe('task-2');
    });
  });

  it('should call onTasksChanged callback', async () => {
    vi.mocked(listTasks).mockResolvedValue(mockTasks);
    const onTasksChanged = vi.fn();

    const { result } = renderHook(
      () => useTaskData({ taskTreeId: 'branch-123', onTasksChanged }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    result.current.addNewTask({
      id: 'task-3',
      title: 'New',
      status: 'todo',
      priority: 'low',
      subtask_count: 0,
      assignees: [],
      dependencies: [],
      created_at: '2024-01-03',
    });

    await waitFor(() => {
      expect(onTasksChanged).toHaveBeenCalled();
    });
  });
});
