/**
 * React Hook for Branch Summaries (React Query version)
 *
 * Provides a clean interface for loading branch summaries using the new
 * bulk API endpoint. Uses React Query for automatic caching and refetching.
 */

import { useQuery } from '@tanstack/react-query';
import { branchService } from '../services/branchService';
import type { BranchSummary, Project } from '../types/api.types';
import type { UseBranchSummariesOptions } from '../types/hookTypes';

// Stable fallback identities, shared by every render and every instance. `?? []` mints a new array
// on every render, and callers memoize on this value: ProjectList derives `taskCounts` from it and
// `useProjectAnimations` writes that object into state while depending on it, so a fresh identity
// per render is an infinite render -> effect -> setState loop. Measured on /dashboard in a COLD
// context (the e2e toolkit's shape - a fresh browser context per viewport, no query cache): React
// logs "Maximum update depth exceeded" until the query resolves, and it does so with NO webSocket
// events possible at all, which is what refuted the WS-churn explanation for that finding.
const NO_BRANCHES: BranchSummary[] = [];
const NO_PROJECTS: Project[] = [];

export function useBranchSummaries(options: UseBranchSummariesOptions = {}) {
  const { projectIds, autoRefresh = false, refreshInterval = 30000 } = options;

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['branchSummaries', projectIds],
    queryFn: async () => {
      if (projectIds?.length) {
        const branches = await branchService.loadProjectSummaries(projectIds);
        return { branches, projects: [] };
      }
      return await branchService.loadUserSummaries();
    },
    refetchInterval: autoRefresh ? refreshInterval : false,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return {
    summaries: data?.branches ?? NO_BRANCHES,
    projects: data?.projects ?? NO_PROJECTS,
    loading: isLoading,
    error: error?.message ?? null,
    refresh: refetch,
    forceRefresh: refetch,
    refreshing: isFetching && !isLoading,
    // Optimistic updates now handled by React Query mutations in components
    removeBranchOptimistically: () => {},
    addBranchOptimistically: () => {},
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
