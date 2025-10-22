/**
 * React Hook for Branch Summaries
 *
 * Provides a clean interface for loading branch summaries using the new
 * bulk API endpoint. Replaces multiple API calls with optimized single requests.
 */

import { useEffect, useState, useCallback } from 'react';
import { branchService } from '../services/branchService';
import type { BranchSummary, ProjectSummary } from '../types/api.types';
import type { UseBranchSummariesOptions, UseBranchSummariesResult } from '../types/hookTypes';
import logger from '../utils/logger';

export function useBranchSummaries(options: UseBranchSummariesOptions = {}): UseBranchSummariesResult {
  const { projectIds, autoRefresh = false, refreshInterval = 30000 } = options;

  const [summaries, setSummaries] = useState<BranchSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummaries = useCallback(async (isRefresh: boolean = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      let result;

      if (projectIds?.length) {
        // Load specific projects
        const branches = await branchService.loadProjectSummaries(projectIds);
        result = { branches, projects: [] }; // Projects not returned for filtered requests
      } else {
        // Load all user summaries
        result = await branchService.loadUserSummaries();
      }

      setSummaries(result.branches);
      setProjects(result.projects);

      logger.debug(`📊 Loaded ${result.branches.length} branch summaries`);

    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to load summaries. Please check your connection.';
      setError(errorMessage);
      logger.error('❌ Branch summaries hook error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectIds]);

  // Manual refresh function
  const refresh = useCallback(async () => {
    await loadSummaries(true);
  }, [loadSummaries]);

  // Force refresh function (aggressive cache clearing)
  const forceRefresh = useCallback(async () => {
    try {
      setRefreshing(true);
      setError(null);

      let result;

      if (projectIds?.length) {
        // Force refresh specific projects (not implemented yet - use regular refresh)
        const branches = await branchService.loadProjectSummaries(projectIds);
        result = { branches, projects: [] };
      } else {
        // Force refresh all user summaries with aggressive cache clearing
        result = await branchService.forceRefreshSummaries();
      }

      setSummaries(result.branches);
      setProjects(result.projects);

      logger.warn(`🚨 FORCE REFRESHED ${result.branches.length} branch summaries (all caches cleared)`);

    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to force refresh summaries. Please check your connection.';
      setError(errorMessage);
      logger.error('❌ Branch summaries force refresh error:', err);
    } finally {
      setRefreshing(false);
    }
  }, [projectIds]);

  // Initial load
  useEffect(() => {
    loadSummaries(false);
  }, [loadSummaries]);

  // Auto-refresh setup
  useEffect(() => {
    if (!autoRefresh || refreshInterval <= 0) {
      return;
    }

    const interval = setInterval(() => {
      if (!loading && !refreshing) {
        refresh();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, loading, refreshing, refresh]);

  // Optimistic update: remove a branch from summaries immediately
  const removeBranchOptimistically = useCallback((branchId: string) => {
    setSummaries(prev => prev.filter(branch => branch.id !== branchId));
    logger.debug(`🗑️ Optimistically removed branch ${branchId} from summaries`);
  }, []);

  // Optimistic update: add a branch to summaries immediately
  const addBranchOptimistically = useCallback((branch: BranchSummary) => {
    setSummaries(prev => [...prev, branch]);
    logger.debug(`➕ Optimistically added branch ${branch.id} to summaries`);
  }, []);

  return {
    summaries,
    projects,
    loading,
    error,
    refresh,
    forceRefresh,
    refreshing,
    removeBranchOptimistically,
    addBranchOptimistically
  };
}

/**
 * Hook for loading summaries of a single project
 */
export function useProjectSummaries(projectId: string) {
  return useBranchSummaries({ projectIds: [projectId] });
}

/**
 * Hook for loading all user summaries with auto-refresh
 */
export function useAllBranchSummaries(refreshInterval: number = 30000) {
  return useBranchSummaries({
    autoRefresh: true,
    refreshInterval
  });
}