import React, { useEffect, useState } from "react";
import { ProjectListProps } from "../../types";
import { ProjectDialogs, ProjectListContent, ProjectListHeader } from "./components";
import { useProjectAnimations, useProjectData, useProjectDialogs } from "./hooks";
import { useWebSocket } from "../../hooks/useWebSocketV2";
import { useAuth } from "../../contexts/AuthContext";

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

  // Auto-expand project when it's selected from URL
  useEffect(() => {
    if (selectedProjectId && !openProjects[selectedProjectId]) {
      setOpenProjects(prev => ({ ...prev, [selectedProjectId]: true }));
    }
  }, [selectedProjectId, openProjects]);

  // WebSocket connection status
  const { user, tokens } = useAuth();
  const { isConnected } = useWebSocket(user?.id || '', tokens?.access_token || '');

  // Custom hooks for data management
  const projectData = useProjectData({ selectedProjectId });

  const {
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
  } = projectData;

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

  // Custom hooks for animations
  const animations = useProjectAnimations({
    projects,
    taskCounts,
  });

  const {
    newBranches,
    fadingOutBranches,
    deletingBranches,
    animatingCounts,
    setDeletingBranches,
    setFadingOutBranches,
  } = animations;

  // Toggle project expand/collapse
  const toggleProject = (projectId: string) => {
    const isOpening = !openProjects[projectId];
    // Simply toggle - branches are already preloaded
    setOpenProjects(prev => ({ ...prev, [projectId]: isOpening }));
  };

  // CRUD operation wrappers with dialog state management
  const handleCreateProjectWrapper = async () => {
    setSaving(true);
    try {
      await handleCreateProject(form);
      closeDialog('create');
    } catch (e) {
      // Error already handled by hook
    } finally {
      setSaving(false);
    }
  };

  const handleEditProjectWrapper = async () => {
    if (!showEdit) return;
    setSaving(true);
    try {
      await handleUpdateProject(showEdit, form);
      closeDialog('edit');
    } catch (e) {
      // Error already handled by hook
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProjectWrapper = async () => {
    if (!showDelete) return;
    setSaving(true);
    setError(null);

    // Close dialog immediately for better UX
    closeDialog('delete');

    try {
      await handleDeleteProject(showDelete);
    } catch (e) {
      // Error already handled by hook
    } finally {
      setSaving(false);
    }
  };

  const handleCreateBranchWrapper = async () => {
    if (!showCreateBranch) return;
    setSaving(true);
    try {
      await handleCreateBranch(showCreateBranch, form);
      closeDialog('createBranch');
    } catch (e) {
      // Error already handled by hook
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBranchWrapper = async () => {
    if (!showDeleteBranch) return;

    const branchId = showDeleteBranch.branch.id;

    // Animation callbacks
    const onFadeoutStart = () => {
      setFadingOutBranches(prev => new Set(prev).add(branchId));
    };

    const onFadeoutComplete = () => {
      setDeletingBranches(prev => new Set(prev).add(branchId));
    };

    setSaving(true);

    try {
      await handleDeleteBranch(showDeleteBranch, onFadeoutStart, onFadeoutComplete);
      closeDialog('deleteBranch');
    } catch (e) {
      // Error already handled by hook
    } finally {
      // Clean up loading states
      setDeletingBranches(prev => {
        const updated = new Set(prev);
        updated.delete(branchId);
        return updated;
      });

      // Clean up animation states
      setFadingOutBranches(prev => {
        const updated = new Set(prev);
        updated.delete(branchId);
        return updated;
      });

      setSaving(false);
    }
  };

  // Form change handler
  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>, field: 'name' | 'description') => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
  };

  // Loading and error states
  if ((loading && projects.length === 0) || loadingBulkSummaries) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-1">
        <div className="animate-spin h-3 w-3 border-2 border-primary border-t-transparent rounded-full"></div>
        {loading ? 'Loading projects...' : 'Loading branch summaries...'}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs text-destructive px-2 py-1">
        Error: {error}
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
        newBranches={newBranches}
        fadingOutBranches={fadingOutBranches}
        deletingBranches={deletingBranches}
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