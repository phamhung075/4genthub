// Custom hook for project management with React Query
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createProject, deleteProject, listProjects, updateProject } from '../api';
import type { Project } from '../types/api.types';
import logger from '../utils/logger';

/**
 * Hook to fetch all projects with caching
 * @returns Query result with projects list, loading state, and error
 */
export const useProjects = () => {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      logger.debug('[useProjects] Fetching projects list');
      const projects = await listProjects();
      logger.debug('[useProjects] Fetched projects:', projects.length);
      return projects;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    refetchOnWindowFocus: false
  });
};

/**
 * Hook to fetch a single project by ID
 * @param projectId Project ID to fetch
 * @returns Query result with project data, loading state, and error
 */
export const useProject = (projectId: string | undefined) => {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: async () => {
      if (!projectId) return null;

      logger.debug('[useProject] Fetching project:', projectId);
      // Find project in the projects list cache
      const projects = await listProjects();
      const project = projects.find(p => p.id === projectId);

      if (!project) {
        throw new Error(`Project ${projectId} not found`);
      }

      return project;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1
  });
};

/**
 * Hook providing mutations for project CRUD operations with optimistic updates
 * @returns Object with create, update, and delete mutation functions
 */
export const useProjectMutations = () => {
  const queryClient = useQueryClient();

  // Create project mutation
  const createMutation = useMutation({
    mutationFn: async (newProject: Partial<Project>) => {
      logger.debug('[useProjectMutations] Creating project:', newProject);
      return await createProject(newProject);
    },
    onMutate: async (newProject) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['projects'] });

      // Snapshot previous value
      const previousProjects = queryClient.getQueryData<Project[]>(['projects']);

      // Optimistically update cache with temporary ID
      if (previousProjects) {
        const optimisticProject: Project = {
          id: `temp-${Date.now()}`,
          name: newProject.name || '',
          description: newProject.description,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        queryClient.setQueryData<Project[]>(['projects'], [...previousProjects, optimisticProject]);
      }

      return { previousProjects };
    },
    onError: (err, _, context) => {
      logger.error('[useProjectMutations] Create failed:', err);
      // Rollback on error
      if (context?.previousProjects) {
        queryClient.setQueryData(['projects'], context.previousProjects);
      }
    },
    onSuccess: (data) => {
      logger.debug('[useProjectMutations] Project created:', data);
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });

  // Update project mutation
  const updateMutation = useMutation({
    mutationFn: async ({ projectId, updates }: { projectId: string; updates: Partial<Project> }) => {
      logger.debug('[useProjectMutations] Updating project', { projectId, updates });
      return await updateProject(projectId, updates);
    },
    onMutate: async ({ projectId, updates }) => {
      await queryClient.cancelQueries({ queryKey: ['projects'] });
      await queryClient.cancelQueries({ queryKey: ['projects', projectId] });

      const previousProjects = queryClient.getQueryData<Project[]>(['projects']);
      const previousProject = queryClient.getQueryData<Project>(['projects', projectId]);

      // Optimistically update projects list
      if (previousProjects) {
        queryClient.setQueryData<Project[]>(
          ['projects'],
          previousProjects.map(p =>
            p.id === projectId ? { ...p, ...updates, updated_at: new Date().toISOString() } : p
          )
        );
      }

      // Optimistically update single project
      if (previousProject) {
        queryClient.setQueryData(['projects', projectId], {
          ...previousProject,
          ...updates,
          updated_at: new Date().toISOString()
        });
      }

      return { previousProjects, previousProject };
    },
    onError: (err, { projectId }, context) => {
      logger.error('[useProjectMutations] Update failed:', err);
      if (context?.previousProjects) {
        queryClient.setQueryData(['projects'], context.previousProjects);
      }
      if (context?.previousProject) {
        queryClient.setQueryData(['projects', projectId], context.previousProject);
      }
    },
    onSuccess: (data, { projectId }) => {
      logger.debug('[useProjectMutations] Project updated:', data);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
    }
  });

  // Delete project mutation
  const deleteMutation = useMutation({
    mutationFn: async (projectId: string) => {
      logger.debug('[useProjectMutations] Deleting project:', projectId);
      return await deleteProject(projectId);
    },
    onMutate: async (projectId) => {
      await queryClient.cancelQueries({ queryKey: ['projects'] });

      const previousProjects = queryClient.getQueryData<Project[]>(['projects']);

      // Optimistically remove from cache
      if (previousProjects) {
        queryClient.setQueryData<Project[]>(
          ['projects'],
          previousProjects.filter(p => p.id !== projectId)
        );
      }

      return { previousProjects };
    },
    onError: (err, _, context) => {
      logger.error('[useProjectMutations] Delete failed:', err);
      if (context?.previousProjects) {
        queryClient.setQueryData(['projects'], context.previousProjects);
      }
    },
    onSuccess: (_, projectId) => {
      logger.debug('[useProjectMutations] Project deleted:', projectId);
      // Remove from cache and invalidate
      queryClient.removeQueries({ queryKey: ['projects', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });

  return {
    createProject: createMutation.mutate,
    createProjectAsync: createMutation.mutateAsync,
    updateProject: updateMutation.mutate,
    updateProjectAsync: updateMutation.mutateAsync,
    deleteProject: deleteMutation.mutate,
    deleteProjectAsync: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    createError: createMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error
  };
};
