import { useEffect, useRef, useState } from "react";
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
  const [animatingCounts, setAnimatingCounts] = useState<Map<string, 'up' | 'down'>>(new Map());

  /**
   * The last counts the effect saw, in a REF rather than in state. It is a memory of the previous
   * run, never something the UI renders, so committing it as state made every run re-render the
   * consumer and re-run the effect - an unbounded update loop whenever `taskCounts` is a fresh
   * object per render. That is exactly what the consumer hands it while the summaries query has
   * no data (`useBranchSummaries` returns `data?.branches ?? []`, a new empty array per render),
   * and the /dashboard update-depth bailout was that loop.
   */
  const previousTaskCounts = useRef<Record<string, number>>({});

  // Detect task count changes and trigger animations
  useEffect(() => {
    const changedBranches = new Map<string, 'up' | 'down'>();
    const previous = previousTaskCounts.current;

    Object.entries(taskCounts).forEach(([branchId, count]) => {
      const previousCount = previous[branchId];
      if (previousCount !== undefined && previousCount !== count) {
        const direction = count > previousCount ? 'up' : 'down';
        changedBranches.set(branchId, direction);
        logger.debug('🎯 COUNT ANIMATION: Count changed for branch', {
          branchId,
          from: previousCount,
          to: count,
          direction
        }, 'useProjectAnimations.ts');
      }
    });

    previousTaskCounts.current = taskCounts;

    if (changedBranches.size === 0) {
      // Nothing changed: no state write, so an equal-but-new `taskCounts` costs one render and stops.
      return;
    }

    // Add branches to animating map with direction
    setAnimatingCounts(prev => new Map([...prev, ...changedBranches]));

    // Remove from animating set after animation completes
    const timer = setTimeout(() => {
      setAnimatingCounts(prev => {
        const newMap = new Map(prev);
        changedBranches.forEach((_, id) => newMap.delete(id));
        return newMap;
      });
    }, 600); // Animation duration

    return () => clearTimeout(timer);
  }, [taskCounts]);

  return {
    animatingCounts,
  };
};
