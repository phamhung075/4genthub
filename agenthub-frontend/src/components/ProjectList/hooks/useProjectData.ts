import React, { useCallback, useEffect, useState } from "react";
import { createBranch, createProject, deleteBranch, deleteProject, Project, updateProject } from "../../../api";
import { useBranchSummaries } from "../../../hooks/useBranchSummaries";
import { useEntityChanges } from "../../../hooks/useChangeSubscription";
import { useAppSelector } from "../../../store/hooks";
import { BranchSummary } from "../../../types";
import logger from "../../../utils/logger";
import { useErrorToast, useSuccessToast } from "../../ui/toast";
import type { UseProjectDataOptions, UseProjectDataReturn, ProjectFormData } from "../../../types/hookTypes";
import type { ChangeNotification } from "../../../services/changePoolService";

export const useProjectData = ({
  selectedProjectId
}: UseProjectDataOptions): UseProjectDataReturn => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use the new bulk API hook for optimized branch summaries
  const {
    summaries: allBranchSummaries,
    projects: projectSummaries,
    loading: loadingBulkSummaries,
    error: bulkSummariesError,
    refresh: refreshBulkSummaries,
    removeBranchOptimistically,
    addBranchOptimistically
  } = useBranchSummaries();

  // Toast notifications
  const showSuccessToast = useSuccessToast();
  const showErrorToast = useErrorToast();

  // Convert bulk summaries to project-keyed format for compatibility with existing UI
  const branchSummaries = React.useMemo(() => {
    const result: Record<string, BranchSummary[]> = {};

    // Group branch summaries by project ID and ensure compatibility fields
    allBranchSummaries.forEach(branch => {
      if (!result[branch.project_id]) {
        result[branch.project_id] = [];
      }

      // Ensure compatibility with existing UI that expects git_branch_name
      const compatibleBranch: BranchSummary = {
        ...branch,
        git_branch_name: branch.name, // UI expects git_branch_name
        // task_count is already provided by backend, no mapping needed
      };

      result[branch.project_id].push(compatibleBranch);
    });

    return result;
  }, [allBranchSummaries]);

  // Get real-time branch updates from WebSocket cascade store
  const cascadeBranches = useAppSelector(state => state.cascade?.branches || {});

  // Extract task counts from bulk summaries and merge with WebSocket updates
  const taskCounts = React.useMemo(() => {
    const counts: Record<string, number> = {};

    // Start with initial data from API
    allBranchSummaries.forEach(branch => {
      // Use standardized task_count property from backend
      counts[branch.id] = branch.task_count || 0;
    });

    // Override with real-time WebSocket updates if available
    Object.entries(cascadeBranches).forEach(([branchId, branchData]: [string, any]) => {
      if (branchData?.task_count !== undefined) {
        counts[branchId] = branchData.task_count;
      }
    });

    return counts;
  }, [allBranchSummaries, cascadeBranches]);

  // Update projects when bulk API returns them
  useEffect(() => {
    if (projectSummaries) {
      logger.debug('✅ Using projects data from bulk API:', projectSummaries);
      setProjects(projectSummaries);
      // Use loading state from bulk API
      setLoading(loadingBulkSummaries);
    }
  }, [projectSummaries, loadingBulkSummaries]);

  const refreshBranchSummaries = useCallback(async () => {
    // Use the bulk API hook's refresh function instead of manual refresh
    logger.debug('🚀 REFRESH DEBUG: refreshBranchSummaries called - this will update counts');
    logger.info('🔄 Refreshing branch summaries using optimized bulk API');
    await refreshBulkSummaries();
    logger.debug('🚀 REFRESH DEBUG: refreshBranchSummaries completed');
  }, [refreshBulkSummaries]);

  // Initial load only - real-time updates handled by useEntityChanges hook
  useEffect(() => {
    logger.debug('ProjectList initial load - using single bulk API call');
    // Only need to refresh branch summaries, which also returns projects
    refreshBranchSummaries();
  }, [refreshBranchSummaries]);

  // Create stable refresh callback for change pool
  const handleDataChange = useCallback((notification?: ChangeNotification) => {
    logger.debug('🚀 CHANGE DEBUG: handleDataChange called - WebSocket event detected', {
      component: 'ProjectList',
      hasNotification: !!notification,
      entityType: notification?.entityType,
      eventType: notification?.eventType,
      entityId: notification?.entityId,
      hasData: !!notification?.data,
      dataKeys: notification?.data ? Object.keys(notification.data) : []
    });

    // VALIDATION: Check if notification has valid data before processing
    // For CREATE and UPDATE events, validate the data has required fields
    if (notification?.entityType === 'branch') {
      const { eventType, data, entityId } = notification;

      // Branch data validation (same pattern as LazyTaskListRefactored.tsx)
      if (eventType === 'created' && data && data.id && (data.name || data.git_branch_name)) {
        logger.debug('✅ [ProjectList] Branch CREATE with valid data', {
          branchId: data.id,
          name: data.name || data.git_branch_name,
          hasAllFields: !!(data.id && (data.name || data.git_branch_name))
        });
        refreshBranchSummaries();
        return;
      } else if (eventType === 'created' && (!data || !data.id || (!data.name && !data.git_branch_name))) {
        // Missing or incomplete branch data - fallback to refresh
        logger.warn('⚠️ [ProjectList] Branch CREATE event has incomplete data (missing id or name)', {
          entityId,
          hasData: !!data,
          hasId: !!data?.id,
          hasName: !!(data?.name || data?.git_branch_name),
          dataKeys: data ? Object.keys(data) : []
        });
        logger.debug('🔄 [ProjectList] Falling back to full refresh due to incomplete branch data');
        refreshBranchSummaries();
        return;
      } else if (eventType === 'updated' && data && data.id) {
        logger.debug('✅ [ProjectList] Branch UPDATE with valid data', {
          branchId: data.id,
          name: data.name || data.git_branch_name
        });
        refreshBranchSummaries();
        return;
      } else if (eventType === 'deleted') {
        // Delete events don't need data validation - just ID is enough
        logger.debug('🗑️ Branch DELETE event detected, triggering immediate refresh:', {
          component: 'ProjectList',
          entityId
        });
        refreshBranchSummaries();
        return;
      }
    }

    // Project data validation
    if (notification?.entityType === 'project') {
      const { eventType, data, entityId } = notification;

      if (eventType === 'created' && data && data.id && data.name) {
        logger.debug('✅ [ProjectList] Project CREATE with valid data', {
          projectId: data.id,
          name: data.name,
          hasAllFields: !!(data.id && data.name)
        });
        refreshBranchSummaries();
        return;
      } else if (eventType === 'created' && (!data || !data.id || !data.name)) {
        // Missing or incomplete project data - fallback to refresh
        logger.warn('⚠️ [ProjectList] Project CREATE event has incomplete data (missing id or name)', {
          entityId,
          hasData: !!data,
          hasId: !!data?.id,
          hasName: !!data?.name,
          dataKeys: data ? Object.keys(data) : []
        });
        logger.debug('🔄 [ProjectList] Falling back to full refresh due to incomplete project data');
        refreshBranchSummaries();
        return;
      } else if (eventType === 'updated' && data && data.id) {
        logger.debug('✅ [ProjectList] Project UPDATE with valid data', {
          projectId: data.id,
          name: data.name
        });
        refreshBranchSummaries();
        return;
      } else if (eventType === 'deleted') {
        // Delete events don't need data validation - just ID is enough
        logger.debug('🗑️ Project DELETE event detected, triggering immediate refresh:', {
          component: 'ProjectList',
          entityId
        });
        refreshBranchSummaries();
        return;
      }
    }

    // For task events or other entity types, standard refresh
    logger.debug('📡 ProjectList: Data change detected (task or other entity), refreshing...', {
      component: 'ProjectList',
      entityType: notification?.entityType
    });
    refreshBranchSummaries();

    logger.debug('🚀 CHANGE DEBUG: handleDataChange completed refresh call', {
      component: 'ProjectList'
    });
  }, [refreshBranchSummaries]);

  // Unified refresh function for UI buttons
  const handleRefresh = useCallback(async () => {
    logger.debug('🔄 Manual refresh triggered');
    // Only need one call - bulk API returns both projects and branches
    await refreshBranchSummaries();
  }, [refreshBranchSummaries]);

  // Subscribe to centralized change pool for real-time updates
  useEntityChanges('ProjectList', ['task', 'project', 'branch'], handleDataChange);

  // CRUD Operations
  const handleCreateProject = async (data: ProjectFormData) => {
    try {
      await createProject({ name: data.name, description: data.description });
      showSuccessToast(
        'Project created successfully',
        `Project "${data.name}" has been created.`
      );
      // Refresh to get updated project list
      await refreshBranchSummaries();
    } catch (e: any) {
      showErrorToast('Failed to create project', e.message);
      setError(e.message);
      throw e;
    }
  };

  const handleUpdateProject = async (project: Project, data: ProjectFormData) => {
    try {
      await updateProject(project.id, { name: data.name, description: data.description });
      showSuccessToast(
        'Project updated successfully',
        `Project has been renamed to "${data.name}".`
      );
      // Refresh to get updated project list
      await refreshBranchSummaries();
    } catch (e: any) {
      showErrorToast('Failed to update project', e.message);
      setError(e.message);
      throw e;
    }
  };

  const handleDeleteProject = async (project: Project) => {
    const projectName = project.name;
    const projectId = project.id;

    // Store previous state for rollback
    const previousProjects = projects;

    // Optimistic update - immediately remove project from UI
    setProjects(prevProjects => prevProjects.filter(p => p.id !== projectId));

    try {
      const result = await deleteProject(projectId);
      if (result.success) {
        // Success - WebSocket will handle notification
        // Don't show API response notification to avoid duplicates
        // Don't refresh - optimistic update already handled it
      } else {
        // Restore the project on failure
        setProjects(previousProjects);
        // Show the specific validation error from backend
        const errorMsg = result.error || result.message || "Failed to delete project";
        // Make error message more user-friendly
        const userFriendlyMsg = errorMsg
          .replace(/\(\d+ branches:/, '(branches:')  // Remove branch count from parentheses
          .replace(/Delete other branches first.*/, 'Please delete all branches except "main" first.')
          .replace(/Delete all tasks first.*/, 'Please delete all tasks from the main branch first.');
        showErrorToast('Cannot Delete Project', userFriendlyMsg);
        setError(userFriendlyMsg);
      }
    } catch (e: any) {
      // Restore the project on error
      setProjects(previousProjects);
      // Handle the case where the API call fails
      logger.error('Delete project error:', e);
      const errorMessage = e.message || "Failed to delete project";
      showErrorToast('Network error', errorMessage);
      setError(errorMessage);
    }
  };

  const handleCreateBranch = async (project: Project, data: ProjectFormData) => {
    try {
      await createBranch(project.id, {
        git_branch_name: data.name,
        description: data.description
      });

      showSuccessToast(
        'Branch created successfully',
        `Branch "${data.name}" has been created in project "${project.name}".`
      );

      // Refresh to get updated project list, then trigger animation
      await refreshBranchSummaries();

      // Note: The animation will be triggered by the useEffect that detects new branches
      logger.debug('Branch created, animation will be triggered by branch detection logic');
    } catch (e: any) {
      showErrorToast('Failed to create branch', e.message);
      setError(e.message);
      throw e;
    }
  };

  const handleDeleteBranch = async (
    dialogState: { project: Project; branch: any }
  ) => {
    const projectId = dialogState.project.id;
    const branchId = dialogState.branch.id;
    const branchName = dialogState.branch.git_branch_name || dialogState.branch.name;

    // Note: Animations are now self-managed by useBranchAnimation hook
    // No need for parent callbacks - the hook handles fadeout/delete animations automatically
    // via branchDeletionTracker.ts

    // Store backup data for rollback
    const backupProjects = [...projects];
    const backupBranch = allBranchSummaries.find(b => b.id === branchId);

    try {
      // 🔥 CRITICAL FIX: Remove from branch summaries IMMEDIATELY (optimistic update)
      // This ensures the branch disappears from UI before WebSocket animation attempts
      removeBranchOptimistically(branchId);
      logger.debug('✅ Optimistically removed branch from summaries:', branchId);

      // Remove from projects state
      setProjects(prev => prev.map(project => {
        if (project.id === projectId && project.git_branchs) {
          const updatedBranches = { ...project.git_branchs };
          delete updatedBranches[branchId];
          return { ...project, git_branchs: updatedBranches };
        }
        return project;
      }));

      logger.debug('Optimistically removed branch from projects state, attempting deletion:', branchId);

      // Attempt actual deletion
      const result = await deleteBranch(branchId);
      logger.debug('Delete result:', result);

      if (result.success) {
        // Success - WebSocket will handle notification
        // Don't show API response notification to avoid duplicates

        // Optionally refresh data from server to ensure consistency
        // But we don't need to since we've already optimistically updated
        logger.debug('Branch deletion successful - UI already updated');
      } else {
        // Backend deletion failed - rollback UI changes
        logger.error('Backend deletion failed, rolling back:', result);
        setProjects(backupProjects);

        // 🔥 CRITICAL FIX: Restore branch to summaries on failure
        if (backupBranch) {
          addBranchOptimistically(backupBranch);
          logger.debug('✅ Restored branch to summaries after failed deletion:', branchId);
        } else {
          // Fallback: refresh to restore correct state
          refreshBranchSummaries();
        }

        const errorMsg = result.error || result.message || "Failed to delete branch";
        showErrorToast(
          'Failed to delete branch',
          errorMsg,
          {
            label: 'Retry',
            onClick: () => handleDeleteBranch(dialogState)
          }
        );
        setError(errorMsg);
      }
    } catch (e: any) {
      // Network/API error - rollback UI changes
      logger.error('Delete branch error, rolling back:', e);
      setProjects(backupProjects);

      // 🔥 CRITICAL FIX: Restore branch to summaries on error
      if (backupBranch) {
        addBranchOptimistically(backupBranch);
        logger.debug('✅ Restored branch to summaries after error:', branchId);
      } else {
        // Fallback: refresh to restore correct state
        refreshBranchSummaries();
      }

      const errorMessage = e.message || "Failed to delete branch";
      showErrorToast(
        'Network error',
        errorMessage,
        {
          label: 'Retry',
          onClick: () => handleDeleteBranch(dialogState)
        }
      );
      setError(errorMessage);
    }
  };

  return {
    projects,
    setProjects,
    branchSummaries,
    taskCounts,
    loading,
    error,
    setError,
    loadingBulkSummaries,
    handleCreateProject,
    handleUpdateProject,
    handleDeleteProject,
    handleCreateBranch,
    handleDeleteBranch,
    handleRefresh,
  };
};