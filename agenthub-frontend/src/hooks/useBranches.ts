// Custom hook for branch management with React Query
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createBranch, deleteBranch, listBranches, updateBranch } from '../api';
import type { Branch } from '../types/api.types';
import logger from '../utils/logger';

/**
 * Hook to fetch all branches for a project with caching
 * @param projectId Project ID to fetch branches for
 * @returns Query result with branches list, loading state, and error
 */
export const useBranches = (projectId: string | undefined) => {
  return useQuery({
    queryKey: ['branches', projectId],
    queryFn: async () => {
      if (!projectId) return [];

      logger.debug('[useBranches] Fetching branches for project:', projectId);
      const branches = await listBranches(projectId);
      logger.debug('[useBranches] Fetched branches:', branches.length);
      return branches;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    refetchOnWindowFocus: false
  });
};

/**
 * Hook to fetch a single branch by ID
 * @param branchId Branch ID to fetch
 * @returns Query result with branch data, loading state, and error
 */
export const useBranch = (branchId: string | undefined) => {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['branches', branchId],
    queryFn: async () => {
      if (!branchId) return null;

      logger.debug('[useBranch] Fetching branch:', branchId);

      // Try to find branch in the branches list cache first
      const allBranchesQueries = queryClient.getQueriesData<Branch[]>({ queryKey: ['branches'] });

      for (const [, branches] of allBranchesQueries) {
        if (branches) {
          const branch = branches.find(b => b.id === branchId);
          if (branch) return branch;
        }
      }

      return null;
    },
    enabled: !!branchId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1
  });
};

/**
 * Hook providing mutations for branch CRUD operations with optimistic updates
 * @returns Object with create, update, and delete mutation functions
 */
export const useBranchMutations = () => {
  const queryClient = useQueryClient();

  // Create branch mutation
  const createMutation = useMutation({
    mutationFn: async ({ projectId, branch }: { projectId: string; branch: Partial<Branch> }) => {
      logger.debug('[useBranchMutations] Creating branch for project:', projectId, branch);
      return await createBranch(projectId, branch);
    },
    onMutate: async ({ projectId, branch }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['branches', projectId] });
      await queryClient.cancelQueries({ queryKey: ['projects', projectId] });

      // Snapshot previous values
      const previousBranches = queryClient.getQueryData<Branch[]>(['branches', projectId]);

      // Optimistically update cache with temporary ID
      if (previousBranches) {
        const optimisticBranch: Branch = {
          id: `temp-${Date.now()}`,
          project_id: projectId,
          name: branch.git_branch_name || branch.name || '',
          git_branch_name: branch.git_branch_name || '',
          description: branch.description,
          status: 'active',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        queryClient.setQueryData<Branch[]>(
          ['branches', projectId],
          [optimisticBranch, ...previousBranches]
        );
      }

      return { previousBranches, projectId };
    },
    onError: (err, { projectId }, context: any) => {
      logger.error('[useBranchMutations] Create failed:', err);
      // Rollback on error
      if (context?.previousBranches) {
        queryClient.setQueryData(['branches', context.projectId], context.previousBranches);
      }
    },
    onSuccess: (data, { projectId }) => {
      logger.debug('[useBranchMutations] Branch created:', data);
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['branches', projectId] });
      // Also invalidate parent project to update branch count
      queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });

  // Update branch mutation
  const updateMutation = useMutation({
    mutationFn: async ({ branchId, updates }: { branchId: string; updates: Partial<Branch> }) => {
      logger.debug('[useBranchMutations] Updating branch:', branchId, updates);
      return await updateBranch(branchId, updates);
    },
    onMutate: async ({ branchId, updates }) => {
      // Find the project_id from existing cache
      let projectId: string | undefined;
      const allBranchesQueries = queryClient.getQueriesData<Branch[]>({ queryKey: ['branches'] });

      for (const [queryKey, branches] of allBranchesQueries) {
        if (branches) {
          const branch = branches.find(b => b.id === branchId);
          if (branch) {
            projectId = branch.project_id;
            break;
          }
        }
      }

      if (projectId) {
        await queryClient.cancelQueries({ queryKey: ['branches', projectId] });
      }

      const previousBranches = projectId
        ? queryClient.getQueryData<Branch[]>(['branches', projectId])
        : undefined;

      // Optimistically update branches list
      if (previousBranches && projectId) {
        queryClient.setQueryData<Branch[]>(
          ['branches', projectId],
          previousBranches.map(b =>
            b.id === branchId ? { ...b, ...updates, updated_at: new Date().toISOString() } : b
          )
        );
      }

      return { previousBranches, projectId };
    },
    onError: (err, { branchId }, context: any) => {
      logger.error('[useBranchMutations] Update failed:', err);
      if (context?.previousBranches && context?.projectId) {
        queryClient.setQueryData(['branches', context.projectId], context.previousBranches);
      }
    },
    onSuccess: (data, { branchId }) => {
      logger.debug('[useBranchMutations] Branch updated:', data);
      const projectId = data.project_id;

      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['branches', projectId] });
        queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
        queryClient.invalidateQueries({ queryKey: ['projects'] });
      }
    }
  });

  // Delete branch mutation
  const deleteMutation = useMutation({
    mutationFn: async (branchId: string) => {
      logger.debug('[useBranchMutations] Deleting branch:', branchId);
      await deleteBranch(branchId);
      return branchId;
    },
    onMutate: async (branchId) => {
      // Find the project_id from existing cache
      let projectId: string | undefined;
      const allBranchesQueries = queryClient.getQueriesData<Branch[]>({ queryKey: ['branches'] });

      for (const [queryKey, branches] of allBranchesQueries) {
        if (branches) {
          const branch = branches.find(b => b.id === branchId);
          if (branch) {
            projectId = branch.project_id;
            break;
          }
        }
      }

      if (projectId) {
        await queryClient.cancelQueries({ queryKey: ['branches', projectId] });
      }

      const previousBranches = projectId
        ? queryClient.getQueryData<Branch[]>(['branches', projectId])
        : undefined;

      // Optimistically remove from cache
      if (previousBranches && projectId) {
        queryClient.setQueryData<Branch[]>(
          ['branches', projectId],
          previousBranches.filter(b => b.id !== branchId)
        );
      }

      return { previousBranches, projectId };
    },
    onError: (err, branchId, context: any) => {
      logger.error('[useBranchMutations] Delete failed:', err);
      if (context?.previousBranches && context?.projectId) {
        queryClient.setQueryData(['branches', context.projectId], context.previousBranches);
      }
    },
    onSuccess: (branchId, _, context: any) => {
      logger.debug('[useBranchMutations] Branch deleted:', branchId);

      if (context?.projectId) {
        queryClient.invalidateQueries({ queryKey: ['branches', context.projectId] });
        queryClient.invalidateQueries({ queryKey: ['projects', context.projectId] });
        queryClient.invalidateQueries({ queryKey: ['projects'] });
        // Invalidate tasks for this branch
        queryClient.invalidateQueries({ queryKey: ['tasks', branchId] });
      }
    }
  });

  return {
    // Create
    createBranch: createMutation.mutate,
    createBranchAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    // Update
    updateBranch: updateMutation.mutate,
    updateBranchAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,

    // Delete
    deleteBranch: deleteMutation.mutate,
    deleteBranchAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error
  };
};
