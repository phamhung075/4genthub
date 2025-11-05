import React, { useEffect, useState } from "react";
import { ProjectListProps } from "../types";
import { ProjectDialogs, ProjectListContent, ProjectListHeader } from "./ProjectList/components";
import { useProjectAnimations, useProjectDialogs } from "./ProjectList/hooks";
import { useAuth } from "../contexts/AuthContext";
import { useProjects, useProjectMutations } from "../hooks/useProjects";
import { useBranchSummaries } from "../hooks/useBranchSummaries";
import { useBranchMutations } from "../hooks/useBranches";
import { useWebSocket } from "../hooks/useWebSocketV2";
import { useRealtimeSync } from "../hooks/useRealtimeSync";
import { BranchSummary, Project } from "../types";
import logger from "../utils/logger";
import { useErrorToast, useSuccessToast } from "./ui/toast";

const ProjectList: React.FC<ProjectListProps> = ({
  onSelect,
  selectedProjectId,
  selectedBranchId,
  onShowGlobalContext,
  onShowProjectDetails,
  onShowBranchDetails
}) => {
  // Derive selection from URL params instead of local state
  const selected = selectedProjectId && selectedBranchId ? `${selectedProjectId}:${selectedBranchId}` : null;

  // State for open/closed projects
  const [openProjects, setOpenProjects] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  // Auto-expand project when it's selected from URL
  useEffect(() => {
    if (selectedProjectId && !openProjects[selectedProjectId]) {
      setOpenProjects(prev => ({ ...prev, [selectedProjectId]: true }));
    }
  }, [selectedProjectId, openProjects]);

  // Auth and WebSocket
  const { user, tokens } = useAuth();
  const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
  const { isConnected } = webSocketClient;

  // React Query hooks for data
  const { data: projects = [], isLoading: loadingProjects, refetch: refetchProjects } = useProjects();
  const {
    summaries: allBranchSummaries,
    loading: loadingBulkSummaries,
    error: bulkSummariesError,
    refresh: refreshBulkSummaries
  } = useBranchSummaries();

  // Real-time WebSocket sync (replaces cascade Redux)
  useRealtimeSync(webSocketClient.client, true);

  // Mutation hooks
  const projectMutations = useProjectMutations();
  const branchMutations = useBranchMutations();

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

  // Extract task counts from bulk summaries (no more Redux cascade needed!)
  const taskCounts = React.useMemo(() => {
    const counts: Record<string, number> = {};

    allBranchSummaries.forEach(branch => {
      // Use standardized task_count property from backend
      counts[branch.id] = branch.task_count || 0;
    });

    return counts;
  }, [allBranchSummaries]);

  // Unified refresh function
  const handleRefresh = React.useCallback(async () => {
    logger.debug('🔄 Manual refresh triggered');
    await Promise.all([
      refetchProjects(),
      refreshBulkSummaries()
    ]);
  }, [refetchProjects, refreshBulkSummaries]);

  // Custom hooks for dialog management
  const dialogs = useProjectDialogs();

  const {
    showCreate,
    showEdit,
    showDelete,
    showCreateBranch,
    showDeleteBranch,
    form,
    saving,
    setSaving,
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    openCreateBranchDialog,
    openDeleteBranchDialog,
    closeDialog,
    setForm,
  } = dialogs;

  // Custom hooks for animations (task count changes only)
  const animations = useProjectAnimations({
    taskCounts,
  });

  const { animatingCounts } = animations;

  // Toggle project expand/collapse
  const toggleProject = (projectId: string) => {
    setOpenProjects(prev => ({ ...prev, [projectId]: !prev[projectId] }));
  };

  // CRUD operation wrappers with dialog state management
  const handleCreateProjectWrapper = async () => {
    setSaving(true);
    try {
      await projectMutations.createProjectAsync({
        name: form.name,
        description: form.description
      });

      showSuccessToast(
        'Project created successfully',
        `Project "${form.name}" has been created.`
      );

      closeDialog('create');
    } catch (e: any) {
      showErrorToast('Failed to create project', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEditProjectWrapper = async () => {
    if (!showEdit) return;
    setSaving(true);
    try {
      await projectMutations.updateProjectAsync({
        projectId: showEdit.id,
        updates: {
          name: form.name,
          description: form.description
        }
      });

      showSuccessToast(
        'Project updated successfully',
        `Project has been renamed to "${form.name}".`
      );

      closeDialog('edit');
    } catch (e: any) {
      showErrorToast('Failed to update project', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProjectWrapper = async () => {
    if (!showDelete) return;
    const projectName = showDelete.name;

    setSaving(true);
    setError(null);

    // Close dialog immediately for better UX
    closeDialog('delete');

    try {
      await projectMutations.deleteProjectAsync(showDelete.id);
      // Success toast will be shown by mutation hook
    } catch (e: any) {
      // Make error message more user-friendly
      const errorMsg = e.message || "Failed to delete project";
      const userFriendlyMsg = errorMsg
        .replace(/\(\d+ branches:/, '(branches:')
        .replace(/Delete other branches first.*/, 'Please delete all branches except "main" first.')
        .replace(/Delete all tasks first.*/, 'Please delete all tasks from the main branch first.');

      showErrorToast('Cannot Delete Project', userFriendlyMsg);
      setError(userFriendlyMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateBranchWrapper = async () => {
    if (!showCreateBranch) return;
    setSaving(true);
    try {
      await branchMutations.createBranchAsync({
        projectId: showCreateBranch.id,
        branch: {
          git_branch_name: form.name,
          description: form.description
        }
      });

      showSuccessToast(
        'Branch created successfully',
        `Branch "${form.name}" has been created in project "${showCreateBranch.name}".`
      );

      closeDialog('createBranch');
    } catch (e: any) {
      showErrorToast('Failed to create branch', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBranchWrapper = async () => {
    if (!showDeleteBranch) return;

    setSaving(true);

    try {
      await branchMutations.deleteBranchAsync(showDeleteBranch.branch.id);

      closeDialog('deleteBranch');
      // Success - mutation hook handles cache updates via optimistic updates
    } catch (e: any) {
      const errorMessage = e.message || "Failed to delete branch";
      showErrorToast(
        'Failed to delete branch',
        errorMessage,
        {
          label: 'Retry',
          onClick: () => handleDeleteBranchWrapper()
        }
      );
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  // Form change handler
  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>, field: 'name' | 'description') => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
  };

  // Combine loading states
  const loading = loadingProjects || loadingBulkSummaries;

  // Loading and error states
  if (loading && projects.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-1">
        <div className="animate-spin h-3 w-3 border-2 border-primary border-t-transparent rounded-full"></div>
        Loading projects...
      </div>
    );
  }

  if (error || bulkSummariesError) {
    return (
      <div className="text-xs text-destructive px-2 py-1">
        Error: {error || bulkSummariesError}
      </div>
    );
  }

  // Main render
  return (
    <div className="flex flex-col gap-2 overflow-visible">
      <ProjectListHeader
        loading={loading}
        loadingBulkSummaries={loadingBulkSummaries}
        isConnected={isConnected}
        onRefresh={handleRefresh}
        onShowGlobalContext={onShowGlobalContext}
        onCreateProject={openCreateDialog}
      />

      <ProjectListContent
        projects={projects}
        branchSummaries={branchSummaries}
        taskCounts={taskCounts}
        openProjects={openProjects}
        selected={selected}
        animatingCounts={animatingCounts}
        onToggleProject={toggleProject}
        onSelectBranch={onSelect}
        onShowProjectDetails={onShowProjectDetails}
        onShowBranchDetails={onShowBranchDetails}
        onCreateBranch={openCreateBranchDialog}
        onEditProject={openEditDialog}
        onDeleteProject={openDeleteDialog}
        onDeleteBranch={openDeleteBranchDialog}
      />

      <ProjectDialogs
        showCreate={showCreate}
        showEdit={showEdit}
        showDelete={showDelete}
        showCreateBranch={showCreateBranch}
        showDeleteBranch={showDeleteBranch}
        form={form}
        saving={saving}
        onCloseCreate={() => closeDialog('create')}
        onCloseEdit={() => closeDialog('edit')}
        onCloseDelete={() => closeDialog('delete')}
        onCloseCreateBranch={() => closeDialog('createBranch')}
        onCloseDeleteBranch={() => closeDialog('deleteBranch')}
        onFormChange={handleFormChange}
        onCreateProject={handleCreateProjectWrapper}
        onEditProject={handleEditProjectWrapper}
        onDeleteProject={handleDeleteProjectWrapper}
        onCreateBranch={handleCreateBranchWrapper}
        onDeleteBranch={handleDeleteBranchWrapper}
      />
    </div>
  );
};

export default ProjectList;
