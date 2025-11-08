import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Task } from '../api';
import { listTasks } from '../api';
import { getFullTask } from '../api-lazy';
import { TaskSummary } from '../types/taskTypes';
import type { UseTaskDataOptions, UseTaskDataReturn } from '../types/hookTypes';

export function useTaskData({ taskTreeId, onTasksChanged }: UseTaskDataOptions): UseTaskDataReturn {
  const queryClient = useQueryClient();

  // Helper function to convert full task to task summary
  const convertToTaskSummary = useCallback((task: any): TaskSummary => {
    const depFromArray = task.dependencies?.length || 0;
    const depFromRelationships = task.dependency_relationships?.depends_on?.length || 0;
    const depFromSummary = task.dependency_summary?.total_dependencies || 0;
    const dependencyCount = Math.max(depFromArray, depFromRelationships, depFromSummary);

    return {
      id: task.id,
      title: task.title,
      status: task.status,
      priority: task.priority,
      subtask_count: task.subtask_count ?? task.subtasks?.length ?? 0,
      assignees: task.assignees || [],
      has_dependencies: dependencyCount > 0,
      has_context: Boolean(task.context_id || task.context_data),
      created_at: task.created_at
    };
  }, []);

  // Main query for task list
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tasks', taskTreeId],
    queryFn: async () => {
      const taskList = await listTasks({ git_branch_id: taskTreeId });
      const validTaskList = Array.isArray(taskList) ? taskList : [];
      const topLevelTasks = validTaskList.filter(task => !task.parent_task_id);

      // Store all tasks (including subtasks) in cache for quick access
      validTaskList.forEach(task => {
        queryClient.setQueryData(['task', task.id], task);
      });

      return {
        summaries: topLevelTasks.map(convertToTaskSummary),
        allTasks: validTaskList
      };
    },
    enabled: !!taskTreeId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Load full task on demand
  const loadFullTask = useCallback(async (taskId: string): Promise<Task | null> => {
    try {
      const task = await queryClient.fetchQuery({
        queryKey: ['task', taskId],
        queryFn: () => getFullTask(taskId),
        staleTime: 5 * 60 * 1000, // 5 minutes for individual tasks
      });
      return task || null;
    } catch (e) {
      return null;
    }
  }, [queryClient]);

  // Update task from external data (e.g., WebSocket)
  const updateTaskFromData = useCallback((taskData: Task) => {
    // Update individual task cache
    queryClient.setQueryData(['task', taskData.id], taskData);

    // Update task list cache if it's a top-level task
    if (!taskData.parent_task_id) {
      queryClient.setQueryData(['tasks', taskTreeId], (old: any) => {
        if (!old) return old;
        const updatedSummaries = old.summaries.map((task: TaskSummary) =>
          task.id === taskData.id ? convertToTaskSummary(taskData) : task
        );
        return { ...old, summaries: updatedSummaries };
      });
    }

    onTasksChanged?.();
  }, [queryClient, taskTreeId, convertToTaskSummary, onTasksChanged]);

  // Add new task
  const addNewTask = useCallback((taskData: Task) => {
    // Add to individual task cache
    queryClient.setQueryData(['task', taskData.id], taskData);

    // Add to task list if it's a top-level task
    if (!taskData.parent_task_id) {
      queryClient.setQueryData(['tasks', taskTreeId], (old: any) => {
        if (!old) return old;
        const newSummary = convertToTaskSummary(taskData);
        return {
          ...old,
          summaries: [newSummary, ...old.summaries]
        };
      });
    }

    onTasksChanged?.();
  }, [queryClient, taskTreeId, convertToTaskSummary, onTasksChanged]);

  // Remove task
  const removeTask = useCallback((taskId: string) => {
    queryClient.removeQueries({ queryKey: ['task', taskId] });
    queryClient.setQueryData(['tasks', taskTreeId], (old: any) => {
      if (!old) return old;
      return {
        ...old,
        summaries: old.summaries.filter((task: TaskSummary) => task.id !== taskId)
      };
    });

    onTasksChanged?.();
  }, [queryClient, taskTreeId, onTasksChanged]);

  return {
    // State
    taskSummaries: data?.summaries ?? [],
    fullTasks: new Map(), // Deprecated: use loadFullTask instead
    totalTasks: data?.summaries?.length ?? 0,
    loading: isLoading,
    error: error?.message ?? null,
    loadingTasks: new Set(), // Deprecated: React Query handles loading states

    // Actions
    loadTaskSummaries: async () => { await refetch(); },
    loadFullTask,
    updateTaskFromData,
    addNewTask,
    removeTask,
    setTotalTasks: () => {}, // No-op: React Query manages this

    // Utilities
    convertToTaskSummary,
  };
}
