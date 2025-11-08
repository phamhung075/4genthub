// Custom hook for subtask management with React Query
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { completeSubtask, createSubtask, deleteSubtask, listSubtasks, updateSubtask } from '../api';
import type { Subtask } from '../types/api.types';
import logger from '../utils/logger';

/**
 * Hook to fetch all subtasks for a parent task with caching
 * @param taskId Parent task ID to fetch subtasks for
 * @returns Query result with subtasks list, loading state, and error
 */
export const useSubtasks = (taskId: string | undefined) => {
  return useQuery({
    queryKey: ['subtasks', taskId],
    queryFn: async () => {
      if (!taskId) return [];

      logger.debug('[useSubtasks] Fetching subtasks for task:', taskId);
      const subtasks = await listSubtasks(taskId);
      logger.debug('[useSubtasks] Fetched subtasks:', subtasks.length);
      return subtasks;
    },
    enabled: !!taskId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    refetchOnWindowFocus: false
  });
};

/**
 * Hook to fetch a single subtask by ID
 * @param subtaskId Subtask ID to fetch
 * @param includeContext Whether to include context data
 * @returns Query result with subtask data, loading state, and error
 */
export const useSubtask = (subtaskId: string | undefined, includeContext: boolean = false) => {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['subtask', subtaskId, includeContext],
    queryFn: async () => {
      if (!subtaskId) return null;

      logger.debug('[useSubtask] Fetching subtask:', subtaskId);
      // Note: getSubtask requires task_id but doesn't use it - we'll need to get it from cache or pass empty string
      // For now, we'll rely on the subtasks list cache
      const allSubtasksQueries = queryClient.getQueriesData<Subtask[]>({ queryKey: ['subtasks'] });

      for (const [, subtasks] of allSubtasksQueries) {
        if (subtasks) {
          const subtask = subtasks.find(s => s.id === subtaskId);
          if (subtask) return subtask;
        }
      }

      return null;
    },
    enabled: !!subtaskId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1
  });
};

/**
 * Hook providing mutations for subtask CRUD operations with optimistic updates
 * @returns Object with create, update, delete, and complete mutation functions
 */
export const useSubtaskMutations = () => {
  const queryClient = useQueryClient();

  // Create subtask mutation
  const createMutation = useMutation({
    mutationFn: async ({ taskId, subtask }: { taskId: string; subtask: Partial<Subtask> }) => {
      logger.debug('[useSubtaskMutations] Creating subtask for task', { taskId, subtask });
      return await createSubtask(taskId, subtask);
    },
    onMutate: async ({ taskId, subtask }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['subtasks', taskId] });
      await queryClient.cancelQueries({ queryKey: ['task', taskId] });

      // Snapshot previous values
      const previousSubtasks = queryClient.getQueryData<Subtask[]>(['subtasks', taskId]);

      // Optimistically update cache with temporary ID
      if (previousSubtasks) {
        const optimisticSubtask: Subtask = {
          id: `temp-${Date.now()}`,
          task_id: taskId,
          title: subtask.title || '',
          description: subtask.description,
          status: subtask.status || 'todo',
          priority: subtask.priority || 'medium',
          assignees: subtask.assignees,
          progress_percentage: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        queryClient.setQueryData<Subtask[]>(
          ['subtasks', taskId],
          [optimisticSubtask, ...previousSubtasks]
        );
      }

      return { previousSubtasks, taskId };
    },
    onError: (err, _, context: any) => {
      logger.error('[useSubtaskMutations] Create failed:', err);
      // Rollback on error
      if (context?.previousSubtasks) {
        queryClient.setQueryData(['subtasks', context.taskId], context.previousSubtasks);
      }
    },
    onSuccess: (data, { taskId }) => {
      logger.debug('[useSubtaskMutations] Subtask created:', data);
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] });
      // Also invalidate parent task to update subtask count
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    }
  });

  // Update subtask mutation
  const updateMutation = useMutation({
    mutationFn: async ({ subtaskId, updates }: { subtaskId: string; updates: Partial<Subtask> }) => {
      logger.debug('[useSubtaskMutations] Updating subtask', { subtaskId, updates });
      return await updateSubtask(subtaskId, updates);
    },
    onMutate: async ({ subtaskId, updates }) => {
      // Find the task_id from existing cache
      let taskId: string | undefined;
      const allSubtasksQueries = queryClient.getQueriesData<Subtask[]>({ queryKey: ['subtasks'] });

      for (const [, subtasks] of allSubtasksQueries) {
        if (subtasks) {
          const subtask = subtasks.find(s => s.id === subtaskId);
          if (subtask) {
            taskId = subtask.task_id;
            break;
          }
        }
      }

      if (taskId) {
        await queryClient.cancelQueries({ queryKey: ['subtasks', taskId] });
      }

      const previousSubtasks = taskId
        ? queryClient.getQueryData<Subtask[]>(['subtasks', taskId])
        : undefined;

      // Optimistically update subtasks list
      if (previousSubtasks && taskId) {
        queryClient.setQueryData<Subtask[]>(
          ['subtasks', taskId],
          previousSubtasks.map(s =>
            s.id === subtaskId ? { ...s, ...updates, updated_at: new Date().toISOString() } : s
          )
        );
      }

      return { previousSubtasks, taskId };
    },
    onError: (err, _, context: any) => {
      logger.error('[useSubtaskMutations] Update failed:', err);
      if (context?.previousSubtasks && context?.taskId) {
        queryClient.setQueryData(['subtasks', context.taskId], context.previousSubtasks);
      }
    },
    onSuccess: (data) => {
      logger.debug('[useSubtaskMutations] Subtask updated:', data);
      const taskId = data.task_id;

      if (taskId) {
        queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] });
        queryClient.invalidateQueries({ queryKey: ['task', taskId] });
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
      }
    }
  });

  // Delete subtask mutation
  const deleteMutation = useMutation({
    mutationFn: async (subtaskId: string) => {
      logger.debug('[useSubtaskMutations] Deleting subtask:', subtaskId);
      await deleteSubtask(subtaskId);
      return subtaskId;
    },
    onMutate: async (subtaskId) => {
      // Find the task_id from existing cache
      let taskId: string | undefined;
      const allSubtasksQueries = queryClient.getQueriesData<Subtask[]>({ queryKey: ['subtasks'] });

      for (const [, subtasks] of allSubtasksQueries) {
        if (subtasks) {
          const subtask = subtasks.find(s => s.id === subtaskId);
          if (subtask) {
            taskId = subtask.task_id;
            break;
          }
        }
      }

      if (taskId) {
        await queryClient.cancelQueries({ queryKey: ['subtasks', taskId] });
      }

      const previousSubtasks = taskId
        ? queryClient.getQueryData<Subtask[]>(['subtasks', taskId])
        : undefined;

      // Optimistically remove from cache
      if (previousSubtasks && taskId) {
        queryClient.setQueryData<Subtask[]>(
          ['subtasks', taskId],
          previousSubtasks.filter(s => s.id !== subtaskId)
        );
      }

      return { previousSubtasks, taskId };
    },
    onError: (err, _, context: any) => {
      logger.error('[useSubtaskMutations] Delete failed:', err);
      if (context?.previousSubtasks && context?.taskId) {
        queryClient.setQueryData(['subtasks', context.taskId], context.previousSubtasks);
      }
    },
    onSuccess: (subtaskId, _, context: any) => {
      logger.debug('[useSubtaskMutations] Subtask deleted:', subtaskId);

      if (context?.taskId) {
        queryClient.invalidateQueries({ queryKey: ['subtasks', context.taskId] });
        queryClient.invalidateQueries({ queryKey: ['task', context.taskId] });
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
      }
    }
  });

  // Complete subtask mutation
  const completeMutation = useMutation({
    mutationFn: async ({
      subtaskId,
      completion_notes
    }: {
      subtaskId: string;
      completion_notes?: string;
    }) => {
      logger.debug('[useSubtaskMutations] Completing subtask:', subtaskId);
      return await completeSubtask(subtaskId, completion_notes);
    },
    onMutate: async ({ subtaskId }) => {
      // Find the task_id from existing cache
      let taskId: string | undefined;
      const allSubtasksQueries = queryClient.getQueriesData<Subtask[]>({ queryKey: ['subtasks'] });

      for (const [, subtasks] of allSubtasksQueries) {
        if (subtasks) {
          const subtask = subtasks.find(s => s.id === subtaskId);
          if (subtask) {
            taskId = subtask.task_id;
            break;
          }
        }
      }

      if (taskId) {
        await queryClient.cancelQueries({ queryKey: ['subtasks', taskId] });
      }

      const previousSubtasks = taskId
        ? queryClient.getQueryData<Subtask[]>(['subtasks', taskId])
        : undefined;

      // Optimistically update to done status
      if (previousSubtasks && taskId) {
        queryClient.setQueryData<Subtask[]>(
          ['subtasks', taskId],
          previousSubtasks.map(s =>
            s.id === subtaskId
              ? { ...s, status: 'done', progress_percentage: 100, updated_at: new Date().toISOString() }
              : s
          )
        );
      }

      return { previousSubtasks, taskId };
    },
    onError: (err, _, context: any) => {
      logger.error('[useSubtaskMutations] Complete failed:', err);
      if (context?.previousSubtasks && context?.taskId) {
        queryClient.setQueryData(['subtasks', context.taskId], context.previousSubtasks);
      }
    },
    onSuccess: (data) => {
      logger.debug('[useSubtaskMutations] Subtask completed:', data);
      const taskId = data.task_id;

      if (taskId) {
        queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] });
        queryClient.invalidateQueries({ queryKey: ['task', taskId] });
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
      }
    }
  });

  return {
    // Create
    createSubtask: createMutation.mutate,
    createSubtaskAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    // Update
    updateSubtask: updateMutation.mutate,
    updateSubtaskAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,

    // Delete
    deleteSubtask: deleteMutation.mutate,
    deleteSubtaskAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,

    // Complete
    completeSubtask: completeMutation.mutate,
    completeSubtaskAsync: completeMutation.mutateAsync,
    isCompleting: completeMutation.isPending,
    completeError: completeMutation.error
  };
};
