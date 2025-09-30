import { useEffect, useState } from "react";
import { Project } from "../../../api";
import logger from "../../../utils/logger";
import type { UseProjectAnimationsOptions, UseProjectAnimationsReturn } from "../../../types/hookTypes";

export const useProjectAnimations = ({
  projects,
  taskCounts
}: UseProjectAnimationsOptions): UseProjectAnimationsReturn => {
  const [deletingBranches, setDeletingBranches] = useState<Set<string>>(new Set());
  const [previousTaskCounts, setPreviousTaskCounts] = useState<Record<string, number>>({});
  const [animatingCounts, setAnimatingCounts] = useState<Map<string, 'up' | 'down'>>(new Map());

  // Animation states for branch creation and deletion
  const [newBranches, setNewBranches] = useState<Set<string>>(new Set());
  const [fadingOutBranches, setFadingOutBranches] = useState<Set<string>>(new Set());
  const [previousBranchIds, setPreviousBranchIds] = useState<Set<string>>(new Set());
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // Detect task count changes and trigger animations
  useEffect(() => {
    const changedBranches = new Map<string, 'up' | 'down'>();

    Object.entries(taskCounts).forEach(([branchId, count]) => {
      const previousCount = previousTaskCounts[branchId];
      if (previousCount !== undefined && previousCount !== count) {
        const direction = count > previousCount ? 'up' : 'down';
        changedBranches.set(branchId, direction);
        console.log('🎯 COUNT ANIMATION: Count changed for branch', branchId, 'from', previousCount, 'to', count, 'direction:', direction);
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

  // Detect new branches and trigger fade-in animations
  useEffect(() => {
    if (isInitialLoad) {
      // Don't animate on initial load, just track current branches
      const currentBranchIds = new Set<string>();
      projects.forEach(project => {
        if (project.git_branchs) {
          Object.keys(project.git_branchs as Record<string, any>).forEach(branchId => {
            currentBranchIds.add(branchId);
          });
        }
      });
      setPreviousBranchIds(currentBranchIds);
      setIsInitialLoad(false);
      return;
    }

    // Get current branch IDs
    const currentBranchIds = new Set<string>();
    projects.forEach(project => {
      if (project.git_branchs) {
        Object.keys(project.git_branchs as Record<string, any>).forEach(branchId => {
          currentBranchIds.add(branchId);
        });
      }
    });

    // Find newly added branches (not in previous set)
    const newlyAddedBranches = Array.from(currentBranchIds).filter(id => !previousBranchIds.has(id));

    if (newlyAddedBranches.length > 0) {
      logger.debug('Detected new branches for animation:', newlyAddedBranches);

      // Add to newBranches for animation
      setNewBranches(prev => {
        const updated = new Set(prev);
        newlyAddedBranches.forEach(id => updated.add(id));
        return updated;
      });

      // Remove from newBranches after animation completes
      setTimeout(() => {
        setNewBranches(prev => {
          const updated = new Set(prev);
          newlyAddedBranches.forEach(id => updated.delete(id));
          return updated;
        });
      }, 300); // Match animation duration
    }

    // Update previous branch IDs for next comparison
    setPreviousBranchIds(currentBranchIds);
  }, [projects, isInitialLoad]);

  return {
    newBranches,
    fadingOutBranches,
    deletingBranches,
    animatingCounts,
    previousTaskCounts,
    isInitialLoad,
    setDeletingBranches,
    setFadingOutBranches,
  };
};