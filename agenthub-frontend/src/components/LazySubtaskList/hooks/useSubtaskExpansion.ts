// useSubtaskExpansion hook - Animation and expansion state management
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useState, useCallback, useRef, useEffect } from "react";
import { Subtask } from "../../../api";
import { SubtaskSummary } from "../../../types/taskTypes";
import type {
  UseSubtaskExpansionReturn,
  AnimationTriggers,
  RowAnimationCallbacks
} from "../../../types/subtaskTypes";
import { detectSubtaskChanges } from "../utils/subtaskHelpers";
import { ANIMATION_CONFIG } from "../constants/subtaskConstants";
import logger from "../../../utils/logger";

/**
 * Custom hook for managing subtask expansion state and animations
 * Handles row animations, expansion tracking, and visual feedback
 */
export function useSubtaskExpansion(
  subtaskSummaries: SubtaskSummary[]
): UseSubtaskExpansionReturn {

  // Expansion state
  const [previousSubtaskIds, setPreviousSubtaskIds] = useState<Set<string>>(new Set());
  const [isOpeningDialog, setIsOpeningDialog] = useState(false);
  const [editingSubtask, setEditingSubtask] = useState<Subtask | null>(null);
  const [showDetails, setShowDetails] = useState<string | null>(null);

  // Animation state
  const [animationTriggers, setAnimationTriggers] = useState<AnimationTriggers>({
    created: new Set(),
    updated: new Set(),
    deleted: new Set()
  });

  // Row animation callback registry
  const rowAnimationCallbacks = useRef<Map<string, RowAnimationCallbacks>>(new Map());

  // Track previous subtasks for change detection
  const previousSubtasksRef = useRef<Map<string, SubtaskSummary>>(new Map());

  /**
   * Register animation callbacks for a subtask row
   */
  const registerRowCallbacks = useCallback((
    subtaskId: string,
    callbacks: RowAnimationCallbacks
  ) => {
    rowAnimationCallbacks.current.set(subtaskId, callbacks);
    logger.debug(`Registered animation callbacks for subtask: ${subtaskId}`);
  }, []);

  /**
   * Unregister animation callbacks for a subtask row
   */
  const unregisterRowCallbacks = useCallback((subtaskId: string) => {
    rowAnimationCallbacks.current.delete(subtaskId);
    logger.debug(`Unregistered animation callbacks for subtask: ${subtaskId}`);
  }, []);

  /**
   * Trigger animation for a specific subtask
   */
  const triggerAnimation = useCallback((
    subtaskId: string,
    type: 'create' | 'update' | 'delete'
  ) => {
    const callbacks = rowAnimationCallbacks.current.get(subtaskId);
    if (!callbacks) {
      logger.debug(`No animation callbacks found for subtask: ${subtaskId}`);
      return;
    }

    try {
      switch (type) {
        case 'create':
          callbacks.playCreateAnimation();
          break;
        case 'update':
          callbacks.playUpdateAnimation();
          break;
        case 'delete':
          callbacks.playDeleteAnimation();
          break;
      }

      logger.debug(`Triggered ${type} animation for subtask: ${subtaskId}`);

    } catch (error) {
      logger.error(`Error triggering ${type} animation for subtask ${subtaskId}:`, error);
    }
  }, []);

  /**
   * Set show details state
   */
  const setShowDetailsState = useCallback((subtaskId: string | null) => {
    setShowDetails(subtaskId);
    logger.debug('Show details state updated:', subtaskId);
  }, []);

  /**
   * Set editing subtask state
   */
  const setEditingSubtaskState = useCallback((subtask: Subtask | null) => {
    setEditingSubtask(subtask);
    logger.debug('Editing subtask state updated:', subtask?.id);
  }, []);

  /**
   * Set dialog opening state with timeout
   */
  const setDialogOpening = useCallback((opening: boolean) => {
    setIsOpeningDialog(opening);

    if (opening) {
      // Auto-clear after timeout to prevent stuck state
      setTimeout(() => {
        setIsOpeningDialog(false);
      }, ANIMATION_CONFIG.ANIMATION_CLEANUP_TIMEOUT);
    }
  }, []);

  /**
   * Process animation triggers based on subtask changes
   */
  const processAnimationTriggers = useCallback(() => {
    const currentSubtasks = subtaskSummaries;
    const previousSubtasks = Array.from(previousSubtasksRef.current.values());

    // Detect changes
    const changes = detectSubtaskChanges(previousSubtasks, currentSubtasks);

    // Update animation triggers
    setAnimationTriggers(changes);

    // Trigger animations with staggered delays
    let delay = 0;

    // Created animations
    changes.created.forEach(subtaskId => {
      setTimeout(() => {
        triggerAnimation(subtaskId, 'create');
      }, delay);
      delay += ANIMATION_CONFIG.ANIMATION_STAGGER_DELAY;
    });

    // Updated animations
    changes.updated.forEach(subtaskId => {
      setTimeout(() => {
        triggerAnimation(subtaskId, 'update');
      }, delay);
      delay += ANIMATION_CONFIG.ANIMATION_STAGGER_DELAY;
    });

    // Delete animations (immediate, no stagger)
    changes.deleted.forEach(subtaskId => {
      triggerAnimation(subtaskId, 'delete');
    });

    // Update previous subtasks reference
    const newPreviousMap = new Map<string, SubtaskSummary>();
    currentSubtasks.forEach(subtask => {
      newPreviousMap.set(subtask.id, subtask);
    });
    previousSubtasksRef.current = newPreviousMap;

    // Update previous IDs set
    setPreviousSubtaskIds(new Set(currentSubtasks.map(s => s.id)));

    logger.debug('Animation triggers processed:', {
      created: changes.created.size,
      updated: changes.updated.size,
      deleted: changes.deleted.size
    });

  }, [subtaskSummaries, triggerAnimation]);

  /**
   * Clear animation triggers after animations complete
   */
  const clearAnimationTriggers = useCallback(() => {
    setTimeout(() => {
      setAnimationTriggers({
        created: new Set(),
        updated: new Set(),
        deleted: new Set()
      });
    }, ANIMATION_CONFIG.ROW_ANIMATION_DURATION + 100);
  }, []);

  // Process animations when subtasks change
  useEffect(() => {
    if (subtaskSummaries.length > 0) {
      processAnimationTriggers();
      clearAnimationTriggers();
    }
  }, [subtaskSummaries, processAnimationTriggers, clearAnimationTriggers]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      rowAnimationCallbacks.current.clear();
    };
  }, []);

  return {
    // State
    previousSubtaskIds,
    animationTriggers,
    isOpeningDialog,
    editingSubtask,
    showDetails,

    // Actions
    registerRowCallbacks,
    unregisterRowCallbacks,
    triggerAnimation,
    setShowDetails: setShowDetailsState,
    setEditingSubtask: setEditingSubtaskState,
    setIsOpeningDialog: setDialogOpening
  };
}