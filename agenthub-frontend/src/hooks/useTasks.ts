// Custom hook for task management with React Query
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { completeTask, createTask, deleteTask, getTask, getTasks, updateTask } from '../api';
import type { Task } from '../types/api.types';
import logger from '../utils/logger';

/**
 * Hook to fetch all tasks for a git branch with caching
 * @param git_branch_id Git branch ID to fetch tasks for
 * @returns Query result with tasks list, loading state, and error
 */
export const useTasks = (git_branch_id: string | undefined) => {
  return useQuery({
    queryKey: ['tasks', git_branch_id],
    queryFn: async () => {
      if (!git_branch_id) return [];

      logger.debug('[useTasks] Fetching tasks for branch:', git_branch_id);
      const response = await getTasks(git_branch_id);
      const tasks = response.tasks || [];
      logger.debug('[useTasks] Fetched tasks:', tasks.length);
      return tasks;
    },
    enabled: !!git_branch_id,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    refetchOnWindowFocus: false
  });
};

/**
 * Hook to fetch a single task by ID
 * @param taskId Task ID to fetch
 * @param includeContext Whether to include context data
 * @returns Query result with task data, loading state, and error
 */
export const useTask = (taskId: string | undefined, includeContext: boolean = false) => {
  return useQuery({
    queryKey: ['task', taskId, includeContext],
    queryFn: async () => {
      if (!taskId) return null;

      logger.debug('[useTask] Fetching task:', taskId);
      const task = await getTask(taskId, { includeContext });
      return task;
    },
    enabled: !!taskId,
    staleTime: 5 * 60 * 1000, // 5 minutes for individual tasks
    gcTime: 10 * 60 * 1000,
    retry: 1
  });
};

/**
 * Hook providing mutations for task CRUD operations with optimistic updates
 * @returns Object with create, update, delete, and complete mutation functions
 */
export const useTaskMutations = () => {
  const queryClient = useQueryClient();

  // Create task mutation
  const createMutation = useMutation({
    mutationFn: async (newTask: Partial<Task>) => {
      logger.debug('[useTaskMutations] Creating task:', newTask);
      return await createTask(newTask);
    },
    onMutate: async (newTask) => {
      if (!newTask.git_branch_id) return {};

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['tasks', newTask.git_branch_id] });

      // Snapshot previous value
      const previousTasks = queryClient.getQueryData<Task[]>(['tasks', newTask.git_branch_id]);

      // Optimistically update cache with temporary ID
      if (previousTasks) {
        const optimisticTask: Task = {
          id: `temp-${Date.now()}`,
          title: newTask.title || '',
          description: newTask.description,
          status: newTask.status || 'todo',
          priority: newTask.priority || 'medium',
          git_branch_id: newTask.git_branch_id,
          project_id: newTask.project_id || '',
          assignees: newTask.assignees || [],
          labels: newTask.labels || [],
          has_dependencies: false,
          has_context: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          subtask_count: 0,
          completed_subtasks: 0
        };

        queryClient.setQueryData<Task[]>(
          ['tasks', newTask.git_branch_id],
          [optimisticTask, ...previousTasks]
        );
      }

      return { previousTasks, git_branch_id: newTask.git_branch_id };
    },
    onError: (err, _, context: any) => {
      logger.error('[useTaskMutations] Create failed:', err);
      // Rollback on error
      if (context?.previousTasks && context?.git_branch_id) {
        queryClient.setQueryData(['tasks', context.git_branch_id], context.previousTasks);
      }
    },
    onSuccess: (createdTask, newTask) => {
      logger.debug('[useTaskMutations] Task created:', createdTask);
      // Update cache directly instead of invalidating to prevent component remounts
      const git_branch_id = newTask.git_branch_id;
      if (git_branch_id) {
        queryClient.setQueryData<Task[]>(
          ['tasks', git_branch_id],
          (oldTasks = []) => {
            // Remove temp optimistic task
            const withoutTemp = oldTasks.filter(t => !t.id.startsWith('temp-'));

            // Check if real task already exists (from WebSocket race condition)
            const realTaskExists = withoutTemp.some(t => t.id === createdTask.id);
            if (realTaskExists) {
              // Update existing task instead of adding duplicate
              logger.debug('[useTaskMutations] Task already exists from WebSocket, updating instead of adding');
              return withoutTemp.map(t => t.id === createdTask.id ? createdTask : t);
            }

            // Add new task (WebSocket hasn't arrived yet)
            return [createdTask, ...withoutTemp];
          }
        );
      }
    }
  });

  // Update task mutation
  const updateMutation = useMutation({
    mutationFn: async ({ taskId, updates }: { taskId: string; updates: Partial<Task> }) => {
      logger.debug('[useTaskMutations] Updating task', { taskId, updates });
      return await updateTask(taskId, updates);
    },
    onMutate: async ({ taskId, updates }) => {
      await queryClient.cancelQueries({ queryKey: ['task', taskId] });

      const previousTask = queryClient.getQueryData<Task>(['task', taskId, false]);
      const git_branch_id = previousTask?.git_branch_id || updates.git_branch_id;

      if (git_branch_id) {
        await queryClient.cancelQueries({ queryKey: ['tasks', git_branch_id] });
      }

      const previousTasks = git_branch_id
        ? queryClient.getQueryData<Task[]>(['tasks', git_branch_id])
        : undefined;

      // Optimistically update single task
      if (previousTask) {
        queryClient.setQueryData(['task', taskId, false], {
          ...previousTask,
          ...updates,
          updated_at: new Date().toISOString()
        });
      }

      // Optimistically update tasks list
      if (previousTasks && git_branch_id) {
        queryClient.setQueryData<Task[]>(
          ['tasks', git_branch_id],
          previousTasks.map(t =>
            t.id === taskId ? { ...t, ...updates, updated_at: new Date().toISOString() } : t
          )
        );
      }

      return { previousTask, previousTasks, git_branch_id };
    },
    onError: (err, { taskId }, context: any) => {
      logger.error('[useTaskMutations] Update failed:', err);
      if (context?.previousTask) {
        queryClient.setQueryData(['task', taskId, false], context.previousTask);
      }
      if (context?.previousTasks && context?.git_branch_id) {
        queryClient.setQueryData(['tasks', context.git_branch_id], context.previousTasks);
      }
    },
    onSuccess: (data, { taskId }) => {
      logger.debug('[useTaskMutations] Task updated:', data);
      const git_branch_id = data.git_branch_id;

      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      if (git_branch_id) {
        queryClient.invalidateQueries({ queryKey: ['tasks', git_branch_id] });
      }
    }
  });

  // Delete task mutation
  const deleteMutation = useMutation({
    mutationFn: async (taskId: string) => {
      logger.debug('[useTaskMutations] Deleting task:', taskId);
      await deleteTask(taskId);
      return taskId;
    },
    onMutate: async (taskId) => {
      const previousTask = queryClient.getQueryData<Task>(['task', taskId, false]);
      const git_branch_id = previousTask?.git_branch_id;

      if (git_branch_id) {
        await queryClient.cancelQueries({ queryKey: ['tasks', git_branch_id] });
      }

      const previousTasks = git_branch_id
        ? queryClient.getQueryData<Task[]>(['tasks', git_branch_id])
        : undefined;

      // Optimistically remove from cache
      if (previousTasks && git_branch_id) {
        queryClient.setQueryData<Task[]>(
          ['tasks', git_branch_id],
          previousTasks.filter(t => t.id !== taskId)
        );
      }

      return { previousTask, previousTasks, git_branch_id };
    },
    onError: (err, _, context: any) => {
      logger.error('[useTaskMutations] Delete failed:', err);
      if (context?.previousTasks && context?.git_branch_id) {
        queryClient.setQueryData(['tasks', context.git_branch_id], context.previousTasks);
      }
    },
    onSuccess: (taskId, _, context: any) => {
      logger.debug('[useTaskMutations] Task deleted:', taskId);
      // Remove from cache and invalidate
      queryClient.removeQueries({ queryKey: ['task', taskId] });
      if (context?.git_branch_id) {
        queryClient.invalidateQueries({ queryKey: ['tasks', context.git_branch_id] });
      }
    }
  });

  // Complete task mutation
  const completeMutation = useMutation({
    mutationFn: async ({
      taskId,
      completion_summary,
      testing_notes
    }: {
      taskId: string;
      completion_summary: string;
      testing_notes?: string;
    }) => {
      logger.debug('[useTaskMutations] Completing task:', taskId);
      return await completeTask(taskId, { completion_summary, testing_notes });
    },
    onMutate: async ({ taskId }) => {
      await queryClient.cancelQueries({ queryKey: ['task', taskId] });

      const previousTask = queryClient.getQueryData<Task>(['task', taskId, false]);
      const git_branch_id = previousTask?.git_branch_id;

      if (git_branch_id) {
        await queryClient.cancelQueries({ queryKey: ['tasks', git_branch_id] });
      }

      const previousTasks = git_branch_id
        ? queryClient.getQueryData<Task[]>(['tasks', git_branch_id])
        : undefined;

      // Optimistically update to done status
      if (previousTask) {
        queryClient.setQueryData(['task', taskId, false], {
          ...previousTask,
          status: 'done',
          progress_percentage: 100,
          updated_at: new Date().toISOString()
        });
      }

      if (previousTasks && git_branch_id) {
        queryClient.setQueryData<Task[]>(
          ['tasks', git_branch_id],
          previousTasks.map(t =>
            t.id === taskId
              ? { ...t, status: 'done', progress_percentage: 100, updated_at: new Date().toISOString() }
              : t
          )
        );
      }

      return { previousTask, previousTasks, git_branch_id };
    },
    onError: (err, { taskId }, context: any) => {
      logger.error('[useTaskMutations] Complete failed:', err);
      if (context?.previousTask) {
        queryClient.setQueryData(['task', taskId, false], context.previousTask);
      }
      if (context?.previousTasks && context?.git_branch_id) {
        queryClient.setQueryData(['tasks', context.git_branch_id], context.previousTasks);
      }
    },
    onSuccess: (data, { taskId }) => {
      logger.debug('[useTaskMutations] Task completed:', data);
      const git_branch_id = data.git_branch_id;

      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      if (git_branch_id) {
        queryClient.invalidateQueries({ queryKey: ['tasks', git_branch_id] });
      }
    }
  });

  return {
    // Create
    createTask: createMutation.mutate,
    createTaskAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    // Update
    updateTask: updateMutation.mutate,
    updateTaskAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,

    // Delete
    deleteTask: deleteMutation.mutate,
    deleteTaskAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,

    // Complete
    completeTask: completeMutation.mutate,
    completeTaskAsync: completeMutation.mutateAsync,
    isCompleting: completeMutation.isPending,
    completeError: completeMutation.error
  };
};
