// Custom hook to manage parent task information for subtask displays

import { useState, useEffect, useCallback } from 'react';
import { getTask, Task } from '../api';
import logger from '../utils/logger';

interface ParentTaskInfo {
  id: string;
  title: string;
  status?: string;
  priority?: string;
}

interface UseParentTaskInfoReturn {
  parentTaskInfo: ParentTaskInfo | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

// Cache for parent task info to avoid repeated API calls
const parentTaskCache = new Map<string, ParentTaskInfo>();

/**
 * Custom hook to fetch and cache parent task information
 * @param parentTaskId The ID of the parent task
 * @returns Parent task information, loading state, error state, and refetch function
 */
export const useParentTaskInfo = (parentTaskId: string): UseParentTaskInfoReturn => {
  const [parentTaskInfo, setParentTaskInfo] = useState<ParentTaskInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchParentTaskInfo = useCallback(async () => {
    if (!parentTaskId) {
      return;
    }

    // Check cache first
    const cached = parentTaskCache.get(parentTaskId);
    if (cached) {
      setParentTaskInfo(cached);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      logger.debug('[useParentTaskInfo] Fetching parent task info for:', parentTaskId);
      const response = await getTask(parentTaskId);

      // Handle both response.task and direct task response formats
      const taskData = response?.task || response;

      if (taskData && taskData.id) {
        const info: ParentTaskInfo = {
          id: taskData.id,
          title: taskData.title || 'Untitled Task',
          status: taskData.status,
          priority: taskData.priority
        };

        // Cache the result
        parentTaskCache.set(parentTaskId, info);
        setParentTaskInfo(info);

        logger.debug('[useParentTaskInfo] Successfully fetched parent task info:', info);
      } else {
        throw new Error('Invalid task data received');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch parent task information';
      logger.error('[useParentTaskInfo] Error fetching parent task:', err);
      setError(errorMessage);

      // Create a fallback info object
      const fallbackInfo: ParentTaskInfo = {
        id: parentTaskId,
        title: 'Unknown Task'
      };
      setParentTaskInfo(fallbackInfo);
    } finally {
      setLoading(false);
    }
  }, [parentTaskId]);

  const refetch = useCallback(() => {
    // Clear cache for this task and refetch
    parentTaskCache.delete(parentTaskId);
    fetchParentTaskInfo();
  }, [parentTaskId, fetchParentTaskInfo]);

  useEffect(() => {
    fetchParentTaskInfo();
  }, [fetchParentTaskInfo]);

  return {
    parentTaskInfo,
    loading,
    error,
    refetch
  };
};

/**
 * Clear the parent task cache (useful for testing or when task info changes)
 */
export const clearParentTaskCache = () => {
  parentTaskCache.clear();
};