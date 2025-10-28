// useSubtaskData hook - Data fetching and management for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useState, useCallback, useRef } from "react";
import { deleteSubtask, getSubtask, listSubtasks, Subtask } from "../../../api";
import { getSubtaskSummaries } from "../../../api-lazy";
import { SubtaskSummary } from "../../../types/taskTypes";
import { taskDeletionTracker } from "../../../services/taskDeletionTracker";
import type { UseSubtaskDataReturn } from "../../../types/subtaskTypes";
import {
  subtaskToSummary,
  isValidSubtaskId,
  logSubtaskError,
  createEmptySubtaskDataState
} from "../utils/subtaskHelpers";
import logger from "../../../utils/logger";

/**
 * Custom hook for managing subtask data fetching and state
 * Handles both summary data (lightweight) and full subtask data (on-demand)
 */
export function useSubtaskData(parentTaskId: string): UseSubtaskDataReturn {
  // Core data state
  const [subtaskSummaries, setSubtaskSummaries] = useState<SubtaskSummary[]>([]);
  const [fullSubtasks, setFullSubtasks] = useState<Map<string, Subtask>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingSubtasks, setLoadingSubtasks] = useState<Set<string>>(new Set());
  const [hasLoaded, setHasLoaded] = useState(false);
  const [subscriptionEnabled, setSubscriptionEnabled] = useState(false);

  /**
   * Load subtask summaries (lightweight data for list display)
   */
  const loadSubtaskSummaries = useCallback(async () => {
    logger.debug('🔄 [loadSubtaskSummaries] STARTING for task:', parentTaskId);
    setLoading(true);
    setError(null);

    try {
      const response = await getSubtaskSummaries(parentTaskId);
      logger.debug('📊 [SubtaskData] API returned subtasks', {
        count: response.subtasks.length,
        subtaskIds: response.subtasks.map(s => s.id)
      });

      // Filter out subtasks that are currently being deleted (during animation)
      const filteredSubtasks = response.subtasks.filter(
        subtask => !taskDeletionTracker.isMarkedForDeletion(subtask.id)
      );

      logger.debug('🗑️ [SubtaskData] Filtered out deleted subtasks', {
        original: response.subtasks.length,
        filtered: filteredSubtasks.length,
        removed: response.subtasks.length - filteredSubtasks.length
      });

      setSubtaskSummaries(filteredSubtasks);

      // Populate fullSubtasks Map with filtered data (exclude deleted subtasks)
      const newFullSubtasks = new Map<string, Subtask>();
      filteredSubtasks.forEach(subtask => {
        newFullSubtasks.set(subtask.id, subtask as Subtask);
      });
      setFullSubtasks(newFullSubtasks);

      setHasLoaded(true);

      // Enable subscription after first successful load
      setTimeout(() => setSubscriptionEnabled(true), 100);

      logger.debug(`🔄 [loadSubtaskSummaries] COMPLETED - Set ${response.subtasks.length} subtasks in state`);

    } catch (e: any) {
      // Handle 400 errors gracefully (task might not exist)
      if (e.status === 400 || e.response?.status === 400) {
        setSubtaskSummaries([]);
        setHasLoaded(true);
        setTimeout(() => setSubscriptionEnabled(true), 100);
        return;
      }

      const errorMessage = e?.message || 'Failed to load subtasks';
      setError(errorMessage);
      logSubtaskError('load summaries', e, { parentTaskId });

    } finally {
      setLoading(false);
    }
  }, [parentTaskId]);

  /**
   * Load full subtasks fallback (when summaries API is not available)
   */
  const loadFullSubtasksFallback = useCallback(async (): Promise<Map<string, Subtask>> => {
    try {
      const subtasks = await listSubtasks(parentTaskId);

      // Convert to summaries
      const summaries: SubtaskSummary[] = subtasks.map(subtaskToSummary);
      setSubtaskSummaries(summaries);

      // Store full subtasks for immediate access
      const subtaskMap = new Map<string, Subtask>();
      subtasks.forEach(subtask => subtaskMap.set(subtask.id, subtask));
      setFullSubtasks(subtaskMap);

      return subtaskMap;

    } catch (e: any) {
      // Handle 400 errors silently for non-existent tasks
      if (e.status === 400 || e.response?.status === 400) {
        setSubtaskSummaries([]);
        const emptyMap = new Map<string, Subtask>();
        setFullSubtasks(emptyMap);
        return emptyMap;
      }

      logSubtaskError('load full subtasks fallback', e, { parentTaskId });
      setError(e?.message || 'Failed to load subtasks');
      return new Map();
    }
  }, [parentTaskId]);

  /**
   * Load subtask by ID (for individual subtask access)
   */
  const loadSubtaskById = useCallback(async (subtaskId: string): Promise<Subtask | null> => {
    if (!isValidSubtaskId(subtaskId)) {
      logger.debug(`Invalid subtask ID format, skipping API call: ${subtaskId}`);
      return null;
    }

    try {
      const subtask = await getSubtask(parentTaskId, subtaskId);

      // Verify subtask belongs to parent task
      if (subtask && subtask.task_id === parentTaskId) {
        return subtask;
      }

      logger.debug(`Subtask ${subtaskId} does not belong to parent task ${parentTaskId}`);
      return null;

    } catch (error: any) {
      // Handle expected errors silently
      if (error?.name === 'NotFoundError' || error?.status === 404 ||
          error?.message?.includes('Invalid subtask ID format')) {
        logger.debug('Subtask not found or invalid format:', {
          subtaskId,
          parentTaskId,
          errorType: error?.name || 'UNKNOWN'
        });
        return null;
      }

      logSubtaskError('load by ID', error, { subtaskId, parentTaskId });
      return null;
    }
  }, [parentTaskId]);

  /**
   * Handle subtask creation (add to local state)
   */
  const handleSubtaskCreated = useCallback((newSubtask: Subtask) => {
    logger.debug('✨ [SubtaskData] handleSubtaskCreated called', {
      subtaskId: newSubtask.id,
      title: newSubtask.title,
      currentCount: subtaskSummaries.length
    });

    // Add to summaries
    const newSummary = subtaskToSummary(newSubtask);
    setSubtaskSummaries(prev => {
      const newCount = prev.length + 1;
      logger.debug('✅ [SubtaskData] State updated', {
        newCount: newCount
      });
      return [...prev, newSummary];
    });

    // Add to full subtasks
    setFullSubtasks(prev => {
      const newMap = new Map(prev);
      newMap.set(newSubtask.id, newSubtask);
      return newMap;
    });
  }, [subtaskSummaries.length]);

  /**
   * Refresh all data (force reload)
   * Non-destructive refresh - let loadSubtaskSummaries handle state updates
   */
  const refreshData = useCallback(async () => {
    logger.debug('🔄 [SubtaskData] refreshData called', {
      timestamp: Date.now()
    });
    await loadSubtaskSummaries();
  }, [loadSubtaskSummaries]);

  return {
    // State
    subtaskSummaries,
    fullSubtasks,
    loading,
    error,
    loadingSubtasks,
    hasLoaded,
    subscriptionEnabled,

    // Actions
    loadSubtaskSummaries,
    loadFullSubtasksFallback,
    loadSubtaskById,
    handleSubtaskCreated,
    refreshData
  };
}