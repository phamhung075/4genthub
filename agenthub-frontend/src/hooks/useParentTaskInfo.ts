// Custom hook to manage parent task information for subtask displays

import { useQuery } from '@tanstack/react-query';
import { getTask } from '../api';
import logger from '../utils/logger';

interface ParentTaskInfo {
  id: string;
  title: string;
  status?: string;
  priority?: string;
}

interface UseParentTaskInfoReturn {
  parentTaskInfo: ParentTaskInfo | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch and cache parent task information using React Query
 * @param parentTaskId The ID of the parent task
 * @returns Parent task information, loading state, error state, and refetch function
 */
export const useParentTaskInfo = (parentTaskId: string): UseParentTaskInfoReturn => {
  const {
    data: parentTaskInfo,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['parentTask', parentTaskId],
    queryFn: async () => {
      if (!parentTaskId) {
        return null;
      }

      logger.debug('[useParentTaskInfo] Fetching parent task info for:', parentTaskId);

      try {
        const taskData = await getTask(parentTaskId);

        if (taskData && taskData.id) {
          const info: ParentTaskInfo = {
            id: taskData.id,
            title: taskData.title || 'Untitled Task',
            status: taskData.status,
            priority: taskData.priority
          };

          logger.debug('[useParentTaskInfo] Successfully fetched parent task info:', info);
          return info;
        }

        throw new Error('Invalid task data received');
      } catch (err: any) {
        logger.error('[useParentTaskInfo] Error fetching parent task:', err);

        // Return fallback info on error
        return {
          id: parentTaskId,
          title: 'Unknown Task'
        };
      }
    },
    enabled: !!parentTaskId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    retry: 2,
    refetchOnWindowFocus: false
  });

  return {
    parentTaskInfo: parentTaskInfo || null,
    isLoading,
    error: error ? (error as Error).message : null,
    refetch: () => { refetch(); }
  };
};
