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

  /**
   * One removal timer per branch. Keyed rather than cleared per effect run: the effect re-runs on
   * every `taskCounts` change, and a cleanup tied to the run would cancel an earlier branch's
   * pending removal the moment a second branch changed, leaving the first animating forever.
   */
  const removalTimers = useRef<Map<string, number>>(new Map());

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

    // Each branch removes itself when its own animation completes; a repeat change restarts it.
    changedBranches.forEach((_, branchId) => {
      const running = removalTimers.current.get(branchId);
      if (running !== undefined) window.clearTimeout(running);
      removalTimers.current.set(branchId, window.setTimeout(() => {
        removalTimers.current.delete(branchId);
        setAnimatingCounts(prev => {
          const newMap = new Map(prev);
          newMap.delete(branchId);
          return newMap;
        });
      }, 600)); // Animation duration
    });
  }, [taskCounts]);

  // Unmount only: an effect cleanup tied to `taskCounts` would cancel another branch's removal.
  useEffect(() => () => {
    removalTimers.current.forEach(handle => window.clearTimeout(handle));
    removalTimers.current.clear();
  }, []);

  return {
    animatingCounts,
  };
};
