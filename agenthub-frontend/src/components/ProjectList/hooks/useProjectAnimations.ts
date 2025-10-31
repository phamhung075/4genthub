import { useEffect, useState } from "react";
import logger from "../../../utils/logger";
import type { UseProjectAnimationsOptions, UseProjectAnimationsReturn } from "../../../types/hookTypes";

/**
 * Hook for managing project-level animations
 * Specifically handles task count change animations
 *
 * Note: Branch animations (create/delete/update) are now handled by useBranchAnimation hook
 */
export const useProjectAnimations = ({
  taskCounts
}: UseProjectAnimationsOptions): UseProjectAnimationsReturn => {
  const [previousTaskCounts, setPreviousTaskCounts] = useState<Record<string, number>>({});
  const [animatingCounts, setAnimatingCounts] = useState<Map<string, 'up' | 'down'>>(new Map());

  // Detect task count changes and trigger animations
  useEffect(() => {
    const changedBranches = new Map<string, 'up' | 'down'>();

    Object.entries(taskCounts).forEach(([branchId, count]) => {
      const previousCount = previousTaskCounts[branchId];
      if (previousCount !== undefined && previousCount !== count) {
        const direction = count > previousCount ? 'up' : 'down';
        changedBranches.set(branchId, direction);
        logger.debug('🎯 COUNT ANIMATION: Count changed for branch', branchId, 'from', previousCount, 'to', count, 'direction:', direction);
      }
    });

    if (changedBranches.size > 0) {
      // Add branches to animating map with direction
      setAnimatingCounts(prev => new Map([...prev, ...changedBranches]));

      // Remove from animating set after animation completes
      setTimeout(() => {
        setAnimatingCounts(prev => {
          const newMap = new Map(prev);
          changedBranches.forEach((_, id) => newMap.delete(id));
          return newMap;
        });
      }, 600); // Animation duration
    }

    // Update previous counts
    setPreviousTaskCounts(taskCounts);
  }, [taskCounts, previousTaskCounts]);

  return {
    animatingCounts,
  };
};