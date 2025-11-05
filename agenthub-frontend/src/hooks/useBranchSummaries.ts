/**
 * React Hook for Branch Summaries (React Query version)
 *
 * Provides a clean interface for loading branch summaries using the new
 * bulk API endpoint. Uses React Query for automatic caching and refetching.
 */

import { useQuery } from '@tanstack/react-query';
import { branchService } from '../services/branchService';
import type { UseBranchSummariesOptions } from '../types/hookTypes';

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
    summaries: data?.branches ?? [],
    projects: data?.projects ?? [],
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
