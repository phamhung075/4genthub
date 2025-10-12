// useSubtaskData hook - Data fetching and management for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useState, useCallback, useRef } from "react";
import { deleteSubtask, getSubtask, listSubtasks, Subtask } from "../../../api";
import { getSubtaskSummaries } from "../../../api-lazy";
import { SubtaskSummary } from "../../../types/taskTypes";
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
    setLoading(true);
    setError(null);

    try {
      const response = await getSubtaskSummaries(parentTaskId);
      setSubtaskSummaries(response.subtasks);

      // Populate fullSubtasks Map with the same data
      const newFullSubtasks = new Map<string, Subtask>();
      response.subtasks.forEach(subtask => {
        newFullSubtasks.set(subtask.id, subtask as Subtask);
      });
      setFullSubtasks(newFullSubtasks);

      setHasLoaded(true);

      // Enable subscription after first successful load
      setTimeout(() => setSubscriptionEnabled(true), 100);

      logger.debug(`Loaded ${response.subtasks.length} subtask summaries for task ${parentTaskId}`);

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
    // Add to summaries
    const newSummary = subtaskToSummary(newSubtask);
    setSubtaskSummaries(prev => [...prev, newSummary]);

    // Add to full subtasks
    setFullSubtasks(prev => {
      const newMap = new Map(prev);
      newMap.set(newSubtask.id, newSubtask);
      return newMap;
    });

    logger.debug('Subtask created and added to local state:', newSubtask.id);
  }, []);

  /**
   * Refresh all data (force reload)
   */
  const refreshData = useCallback(async () => {
    setHasLoaded(false);
    setFullSubtasks(new Map());
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