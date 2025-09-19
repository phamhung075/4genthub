import Cookies from "js-cookie";
import { ChevronDown, ChevronRight, Eye, Folder, GitBranchPlus, Globe, Pencil, Plus, Trash2 } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import { createBranch, createProject, deleteBranch, deleteProject, listProjects, Project, updateProject } from "../api";
import { BranchSummary, getBranchSummaries } from "../api-lazy";
import { cn } from "../lib/utils";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { RefreshButton } from "./ui/refresh-button";
import { ShimmerBadge } from "./ui/shimmer-badge";
import { ShimmerButton } from "./ui/shimmer-button";
import { useErrorToast, useSuccessToast } from "./ui/toast";
import { useEntityChanges } from "../hooks/useChangeSubscription";
import logger from "../utils/logger";

interface ProjectListProps {
  onSelect?: (projectId: string, branchId: string) => void;
  refreshKey?: number; // Add refresh trigger
  selectedProjectId?: string; // Currently selected project ID from URL
  selectedBranchId?: string; // Currently selected branch ID from URL
  onShowGlobalContext?: () => void; // Handler for showing global context
  onShowProjectDetails?: (project: Project) => void; // Handler for showing project details
  onShowBranchDetails?: (project: Project, branch: any) => void; // Handler for showing branch details
}

const ProjectList: React.FC<ProjectListProps> = ({ onSelect, refreshKey, selectedProjectId, selectedBranchId, onShowGlobalContext, onShowProjectDetails, onShowBranchDetails }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Derive selection from URL params instead of local state
  const selected = selectedProjectId && selectedBranchId ? `${selectedProjectId}:${selectedBranchId}` : null;

  // State declarations - moved openProjects before useEffect that uses it
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState<Project | null>(null);
  const [showDelete, setShowDelete] = useState<Project | null>(null);
  const [showDeleteBranch, setShowDeleteBranch] = useState<{ project: Project; branch: any } | null>(null);
  const [showCreateBranch, setShowCreateBranch] = useState<Project | null>(null);
  const [form, setForm] = useState<{ name: string; description: string }>({ name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [openProjects, setOpenProjects] = useState<Record<string, boolean>>({});

  // Auto-expand project when it's selected from URL
  useEffect(() => {
    if (selectedProjectId && !openProjects[selectedProjectId]) {
      setOpenProjects(prev => ({ ...prev, [selectedProjectId]: true }));
    }
  }, [selectedProjectId, openProjects]);
  const [taskCounts, setTaskCounts] = useState<Record<string, number>>({});
  const [branchSummaries, setBranchSummaries] = useState<Record<string, BranchSummary[]>>({});
  const [loadingBranches, setLoadingBranches] = useState<Record<string, boolean>>({});
  const [deletingBranches, setDeletingBranches] = useState<Set<string>>(new Set());
  const [previousTaskCounts, setPreviousTaskCounts] = useState<Record<string, number>>({});

  // Animation states for branch creation and deletion
  const [newBranches, setNewBranches] = useState<Set<string>>(new Set());
  const [fadingOutBranches, setFadingOutBranches] = useState<Set<string>>(new Set());
  const [previousBranchIds, setPreviousBranchIds] = useState<Set<string>>(new Set());
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  // Toast notifications
  const showSuccessToast = useSuccessToast();
  const showErrorToast = useErrorToast();

  const toggleProject = (projectId: string) => {
    const isOpening = !openProjects[projectId];
    // Simply toggle - branches are already preloaded
    setOpenProjects(prev => ({ ...prev, [projectId]: isOpening }));
  };



  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const projectsData = await listProjects();
      logger.debug('Fetched projects data:', projectsData);
      setProjects(projectsData);

      // Extract task counts from the project data directly (no additional API calls needed)
      const counts: Record<string, number> = {};
      for (const project of projectsData) {
        if (project.git_branchs) {
          for (const tree of Object.values(project.git_branchs)) {
            // Use task_count from API response if available, otherwise fallback to 0
            counts[tree.id] = tree.task_count ?? 0;

            // Check if task count changed and show notification
            const prevCount = taskCounts[tree.id] ?? 0;
            const newCount = tree.task_count ?? 0;

            if (prevCount !== newCount && taskCounts[tree.id] !== undefined) {
              // Task count changed!
              // Task count change notifications are now handled by WebSocket service
              // to avoid duplicate notifications
              /*
              if (newCount > prevCount) {
                const diff = newCount - prevCount;
                showSuccessToast(
                  '🎉 New task detected!',
                  `${diff} new task${diff > 1 ? 's' : ''} added to branch "${tree.name}" in project "${project.name}"`
                );
              } else if (newCount < prevCount) {
                const diff = prevCount - newCount;
                showSuccessToast(
                  '✅ Task completed or removed',
                  `${diff} task${diff > 1 ? 's' : ''} removed from branch "${tree.name}" in project "${project.name}"`
                );
              }
              */
            }
          }
        }
      }
      setTaskCounts(counts);
      logger.debug('Updated task counts:', counts);

      // Preload branch summaries for all projects to avoid loading flash
      const token = Cookies.get('access_token');
      if (token) {
        const branchPromises = projectsData.map(async (project) => {
          try {
            const summaries = await getBranchSummaries(project.id);
            if (summaries.branches && summaries.branches.length > 0) {
              return { projectId: project.id, branches: summaries.branches };
            }
            return null;
          } catch (error) {
            logger.error(`Failed to load branches for project ${project.id}:`, error);
            return null;
          }
        });

        const branchResults = await Promise.all(branchPromises);
        const newBranchSummaries: Record<string, BranchSummary[]> = {};

        branchResults.forEach(result => {
          if (result) {
            newBranchSummaries[result.projectId] = result.branches;
          }
        });

        setBranchSummaries(newBranchSummaries);
        logger.debug('Preloaded branch summaries for all projects');
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [showSuccessToast]);

  const refreshOpenBranchSummaries = useCallback(async () => {
    // Check if user is authenticated
    const token = Cookies.get('access_token');
    if (!token) {
      logger.debug('User not authenticated, skipping branch summaries refresh');
      return;
    }

    // Refresh summaries for all currently open projects
    const openProjectIds = Object.entries(openProjects)
      .filter(([_, isOpen]) => isOpen)
      .map(([projectId, _]) => projectId);

    if (openProjectIds.length === 0) {
      return; // No open projects to refresh
    }

    logger.debug('Refreshing branch summaries for open projects:', openProjectIds);
    
    // Clear existing branch summaries for open projects to force fresh data
    const clearedSummaries: Record<string, BranchSummary[]> = {};
    for (const projectId of openProjectIds) {
      clearedSummaries[projectId] = [];
    }
    setBranchSummaries(prev => ({ ...prev, ...clearedSummaries }));

    // Load branch summaries for each open project
    const refreshPromises = openProjectIds.map(async (projectId) => {
      try {
        const summaries = await getBranchSummaries(projectId);
        return { projectId, summaries };
      } catch (error) {
        logger.error(`Error refreshing branch summaries for project ${projectId}:`, error);
        return null;
      }
    });

    const results = await Promise.all(refreshPromises);

    // Update state with new summaries
    const newBranchSummaries: Record<string, BranchSummary[]> = {};
    const newTaskCounts: Record<string, number> = {};

    for (const result of results) {
      if (result) {
        newBranchSummaries[result.projectId] = result.summaries.branches;
        
        // Update task counts from the optimized response
        for (const branch of result.summaries.branches) {
          // Use task_count field which is set by getBranchSummaries
          const taskCount = branch.task_count || branch.task_counts?.total || 0;
          newTaskCounts[branch.id] = taskCount;
          logger.debug(`Updated task count for branch ${branch.git_branch_name || branch.name} (${branch.id}): ${taskCount}`);
        }
      }
    }

    // Replace state completely (not merge) to ensure fresh data
    setBranchSummaries(newBranchSummaries);
    setTaskCounts(newTaskCounts);
    
    logger.debug('Branch summaries refreshed successfully with fresh data');
  }, [openProjects]);

  useEffect(() => {
    logger.debug('ProjectList refreshKey changed:', refreshKey);
    // Clear all cached branch summaries to force fresh reload
    setBranchSummaries({});
    setTaskCounts({});

    // Fetch projects which also preloads all branches
    fetchProjects();
  }, [refreshKey, fetchProjects]);

  // Create stable refresh callback for change pool
  const handleDataChange = useCallback(() => {
    logger.debug('📡 ProjectList: Data change detected, refreshing...');
    // Refresh when entity events occur
    fetchProjects();
    // Note: We don't need to check openProjects here since branches are preloaded
  }, [fetchProjects]);

  // Subscribe to centralized change pool for real-time updates
  useEntityChanges('ProjectList', ['task', 'project', 'branch'], handleDataChange);

  // Detect new branches and trigger fade-in animations
  useEffect(() => {
    if (isInitialLoad) {
      // Don't animate on initial load, just track current branches
      const currentBranchIds = new Set<string>();
      projects.forEach(project => {
        if (project.git_branchs) {
          Object.keys(project.git_branchs).forEach(branchId => {
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
        Object.keys(project.git_branchs).forEach(branchId => {
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
  }, [projects, isInitialLoad]); // Remove previousBranchIds from dependencies

  const handleCreate = async () => {
    setSaving(true);
    try {
      await createProject({ name: form.name, description: form.description });
      showSuccessToast(
        'Project created successfully',
        `Project "${form.name}" has been created.`
      );
      setShowCreate(false);
      setForm({ name: "", description: "" });
      fetchProjects();
    } catch (e: any) {
      showErrorToast('Failed to create project', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateBranch = async () => {
    if (!showCreateBranch) return;
    setSaving(true);
    try {
      const result = await createBranch(showCreateBranch.id, {
        git_branch_name: form.name,
        description: form.description
      });

      showSuccessToast(
        'Branch created successfully',
        `Branch "${form.name}" has been created in project "${showCreateBranch.name}".`
      );
      setShowCreateBranch(null);
      setForm({ name: "", description: "" });

      // Fetch projects first, then trigger animation
      await fetchProjects();

      // Note: The animation will be triggered by the useEffect that detects new branches
      logger.debug('Branch created, animation will be triggered by branch detection logic');

    } catch (e: any) {
      showErrorToast('Failed to create branch', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async () => {
    if (!showEdit) return;
    setSaving(true);
    try {
      await updateProject(showEdit.id, { name: form.name, description: form.description });
      showSuccessToast(
        'Project updated successfully',
        `Project has been renamed to "${form.name}".`
      );
      setShowEdit(null);
      setForm({ name: "", description: "" });
      fetchProjects();
    } catch (e: any) {
      showErrorToast('Failed to update project', e.message);
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!showDelete) return;
    setSaving(true);
    setError(null);
    
    const projectToDelete = showDelete;
    const projectName = projectToDelete.name;
    const projectId = projectToDelete.id;
    
    // Store previous state for rollback
    const previousProjects = projects;
    
    // Optimistic update - immediately remove project from UI
    setProjects(prevProjects => prevProjects.filter(p => p.id !== projectId));
    
    // Close dialog immediately for better UX
    setShowDelete(null);
    
    try {
      const result = await deleteProject(projectId);
      if (result.success) {
        showSuccessToast(
          'Project deleted successfully',
          `Project "${projectName}" has been removed.`
        );
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
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBranch = async () => {
    if (!showDeleteBranch) return;

    const projectId = showDeleteBranch.project.id;
    const branchId = showDeleteBranch.branch.id;
    const branchName = showDeleteBranch.branch.git_branch_name || showDeleteBranch.branch.name;

    // Start fade-out animation first
    setFadingOutBranches(prev => new Set(prev).add(branchId));
    setSaving(true);

    // Wait for fade-out animation to complete before proceeding
    setTimeout(async () => {
      // Mark branch as being deleted (for loading state)
      setDeletingBranches(prev => new Set(prev).add(branchId));

      // Store backup data for rollback
      const backupProjects = [...projects];
      const backupBranchSummaries = { ...branchSummaries };
      const backupTaskCounts = { ...taskCounts };
    
    // Optimistically remove the branch from UI
    try {
      // Remove from projects state
      setProjects(prev => prev.map(project => {
        if (project.id === projectId && project.git_branchs) {
          const updatedBranches = { ...project.git_branchs };
          delete updatedBranches[branchId];
          return { ...project, git_branchs: updatedBranches };
        }
        return project;
      }));
      
      // Remove from branch summaries
      setBranchSummaries(prev => ({
        ...prev,
        [projectId]: prev[projectId]?.filter(branch => branch.id !== branchId) || []
      }));
      
      // Remove from task counts
      setTaskCounts(prev => {
        const updated = { ...prev };
        delete updated[branchId];
        return updated;
      });
      
      logger.debug('Optimistically removed branch from UI, attempting deletion:', branchId);
      
      // Attempt actual deletion
      const result = await deleteBranch(branchId);
      logger.debug('Delete result:', result);
      
      if (result.success) {
        // Success! Show success message
        showSuccessToast(
          'Branch deleted successfully', 
          `Branch "${branchName}" has been removed from the project.`
        );
        setShowDeleteBranch(null);
        
        // Optionally refresh data from server to ensure consistency
        // But we don't need to since we've already optimistically updated
        logger.debug('Branch deletion successful - UI already updated');
      } else {
        // Backend deletion failed - rollback UI changes
        logger.error('Backend deletion failed, rolling back:', result);
        setProjects(backupProjects);
        setBranchSummaries(backupBranchSummaries);
        setTaskCounts(backupTaskCounts);
        
        const errorMsg = result.error || result.message || "Failed to delete branch";
        showErrorToast(
          'Failed to delete branch',
          errorMsg,
          {
            label: 'Retry',
            onClick: () => handleDeleteBranch()
          }
        );
        setError(errorMsg);
      }
    } catch (e: any) {
      // Network/API error - rollback UI changes
      logger.error('Delete branch error, rolling back:', e);
      setProjects(backupProjects);
      setBranchSummaries(backupBranchSummaries);
      setTaskCounts(backupTaskCounts);
      
      const errorMessage = e.message || "Failed to delete branch";
      showErrorToast(
        'Network error',
        errorMessage,
        {
          label: 'Retry',
          onClick: () => handleDeleteBranch()
        }
      );
      setError(errorMessage);
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
    }, 300); // Animation duration
  };

  if (loading && projects.length === 0) return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-1">
      <div className="animate-spin h-3 w-3 border-2 border-primary border-t-transparent rounded-full"></div>
      Loading projects...
    </div>
  );
  if (error) return <div className="text-xs text-destructive px-2 py-1">Error: {error}</div>;

  return (
    <div className="flex flex-col gap-2 overflow-visible">
      {/* Mobile-optimized header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-2">
        {/* Title section */}
        <div className="flex items-center justify-between sm:justify-start">
          <span className="font-bold text-base sm:text-lg">Projects</span>
          {/* Refresh button on mobile - next to title */}
          <RefreshButton 
            onClick={fetchProjects}
            loading={loading}
            className="sm:hidden"
            size="icon"
            title="Refresh projects"
          />
        </div>
        
        {/* Action buttons - responsive layout */}
        <div className="flex gap-2 justify-end sm:w-auto">
          {/* Hidden refresh on desktop (shown in different position) */}
          <RefreshButton 
            onClick={fetchProjects}
            loading={loading}
            className="hidden sm:flex lg:hidden"
            size="icon"
            title="Refresh projects"
          />
          <RefreshButton 
            onClick={fetchProjects}
            loading={loading}
            className="hidden lg:flex"
            size="sm"
          />
          
          {/* Global context button */}
          <ShimmerButton 
            size="sm" 
            variant="outline" 
            onClick={() => onShowGlobalContext && onShowGlobalContext()}
            aria-label="View/Edit Global Context"
            title="View and Edit Global Context"
            className="flex-1 sm:flex-initial min-w-0"
          >
            <Globe className="w-4 h-4 lg:mr-2" />
            <span className="hidden lg:inline">Global</span>
          </ShimmerButton>
          
          {/* New project button */}
          <ShimmerButton 
            size="sm" 
            variant="default" 
            onClick={() => { setShowCreate(true); setForm({ name: "", description: "" }); }}
            className="flex-1 sm:flex-initial min-w-0"
            title="Create New Project"
          >
            <Plus className="w-4 h-4 lg:mr-2" />
            <span className="hidden lg:inline">New Project</span>
          </ShimmerButton>
        </div>
      </div>
      {projects.length === 0 ? (
        <div className="text-xs text-muted-foreground">No projects found.</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {projects.map((project) => (
            <li key={project.id}>
              <div
                className="group relative flex items-center justify-between p-2 rounded-md hover:bg-background-hover transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2 flex-1" onClick={() => toggleProject(project.id)}>
                  {openProjects[project.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  <Folder className="w-4 h-4" />
                  <span className="font-semibold text-sm truncate text-left" title={project.name}>{project.name}</span>
                  <div className="flex gap-1 ml-2">
                    {project.git_branchs && Object.keys(project.git_branchs).length > 0 && (
                      <ShimmerBadge variant={openProjects[project.id] ? "secondary" : "outline"} className="text-xs">
                        {Object.keys(project.git_branchs).length} {Object.keys(project.git_branchs).length === 1 ? 'branch' : 'branches'}
                      </ShimmerBadge>
                    )}
                    {(() => {
                      const totalTasks = project.git_branchs ? 
                        Object.values(project.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0) : 0;
                      return totalTasks > 0 ? (
                        <ShimmerBadge variant="default" className="text-xs">
                          {totalTasks} {totalTasks === 1 ? 'task' : 'tasks'}
                        </ShimmerBadge>
                      ) : null;
                    })()}
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                  <ShimmerButton 
                    size="icon" 
                    variant="ghost" 
                    className="h-7 w-7" 
                    aria-label="View Project Details" 
                    title="View Project Details"
                    onClick={() => onShowProjectDetails && onShowProjectDetails(project)}
                  >
                    <Eye className="w-3 h-3" />
                  </ShimmerButton>
                  <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Create Branch" onClick={() => { setShowCreateBranch(project); setForm({ name: "", description: "" }); }}>
                    <GitBranchPlus className="w-3 h-3" />
                  </ShimmerButton>
                  <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Edit" onClick={() => { setShowEdit(project); setForm({ name: project.name, description: project.description || "" }); }}>
                    <Pencil className="w-3 h-3" />
                  </ShimmerButton>
                  <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Delete" onClick={() => setShowDelete(project)}>
                    <Trash2 className="w-3 h-3 text-destructive" />
                  </ShimmerButton>
                </div>
              </div>
              <ul className="flex flex-col gap-1 ml-8 mt-1" style={{ display: openProjects[project.id] ? 'flex' : 'none' }}>
                  {branchSummaries[project.id] ? (
                    // Use optimized branch summaries if available
                    branchSummaries[project.id].map((branch) => (
                      <li key={branch.id}>
                        <div className={cn(
                          "group relative flex items-center gap-1 transition-all duration-300 ease-in-out",
                          // Fade-in animation for new branches
                          newBranches.has(branch.id) && "opacity-0 -translate-x-2.5",
                          !newBranches.has(branch.id) && "opacity-100 translate-x-0",
                          // Fade-out animation for deleting branches
                          fadingOutBranches.has(branch.id) && "opacity-0 -translate-x-2.5 pointer-events-none",
                          // Loading state for deletion process
                          deletingBranches.has(branch.id) && !fadingOutBranches.has(branch.id) && "opacity-50 pointer-events-none"
                        )}>
                          <span className="text-muted-foreground">—</span>
                          <ShimmerButton
                            size="sm"
                            variant={selected === `${project.id}:${branch.id}` ? "default" : "ghost"}
                            className={cn(
                              "flex-1 justify-start text-xs text-left",
                              selected === `${project.id}:${branch.id}` && "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-700"
                            )}
                            onClick={() => {
                              onSelect && onSelect(project.id, branch.id);
                            }}
                          >
                            <span className="truncate text-left flex-1">{branch.git_branch_name || branch.name}</span>
                            <div className="flex items-center gap-1">
                              <ShimmerBadge variant="secondary" className="text-xs">
                                {branch.task_count || branch.task_counts?.total || 0}
                              </ShimmerBadge>
                              {branch.has_urgent_tasks && (
                                <ShimmerBadge variant="destructive" className="text-xs">!</ShimmerBadge>
                              )}
                              {branch.is_completed && (
                                <ShimmerBadge variant="secondary" className="text-xs text-green-600">✓</ShimmerBadge>
                              )}
                            </div>
                          </ShimmerButton>
                          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                            <ShimmerButton 
                              size="icon" 
                              variant="ghost" 
                              className="h-6 w-6"
                              onClick={() => onShowBranchDetails && onShowBranchDetails(project, branch)}
                              aria-label="View Branch Details"
                              title="View Branch Details"
                            >
                              <Eye className="w-3 h-3" />
                            </ShimmerButton>
                            {(branch.git_branch_name || branch.name) !== 'main' && (
                              <ShimmerButton 
                                size="icon" 
                                variant="ghost" 
                                className="h-6 w-6"
                                onClick={() => setShowDeleteBranch({ project, branch })}
                                disabled={deletingBranches.has(branch.id)}
                                aria-label={deletingBranches.has(branch.id) ? "Deleting Branch..." : "Delete Branch"}
                              >
                                {deletingBranches.has(branch.id) ? (
                                  <div className="animate-spin h-3 w-3 border-2 border-destructive border-t-transparent rounded-full" />
                                ) : (
                                  <Trash2 className="w-3 h-3 text-destructive" />
                                )}
                              </ShimmerButton>
                            )}
                          </div>
                        </div>
                      </li>
                    ))
                  ) : project.git_branchs ? (
                    // Fallback to original branch data if optimized not loaded
                    Object.values(project.git_branchs).map((tree) => (
                      <li key={tree.id}>
                        <div className={cn(
                          "group relative flex items-center gap-1 transition-all duration-300 ease-in-out",
                          // Fade-in animation for new branches
                          newBranches.has(tree.id) && "opacity-0 -translate-x-2.5",
                          !newBranches.has(tree.id) && "opacity-100 translate-x-0",
                          // Fade-out animation for deleting branches
                          fadingOutBranches.has(tree.id) && "opacity-0 -translate-x-2.5 pointer-events-none",
                          // Loading state for deletion process
                          deletingBranches.has(tree.id) && !fadingOutBranches.has(tree.id) && "opacity-50 pointer-events-none"
                        )}>
                          <span className="text-muted-foreground">—</span>
                          <ShimmerButton
                            size="sm"
                            variant={selected === `${project.id}:${tree.id}` ? "secondary" : "ghost"}
                            className="flex-1 justify-start text-xs text-left"
                            onClick={() => {
                              onSelect && onSelect(project.id, tree.id);
                            }}
                          >
                            <span className="truncate text-left flex-1">{tree.git_branch_name || tree.name}</span>
                            <ShimmerBadge variant="secondary" className="text-xs ml-2">
                              {tree.task_count !== undefined ? tree.task_count : (taskCounts[tree.id] ?? 0)}
                            </ShimmerBadge>
                          </ShimmerButton>
                          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                            <ShimmerButton 
                              size="icon" 
                              variant="ghost" 
                              className="h-6 w-6"
                              onClick={() => onShowBranchDetails && onShowBranchDetails(project, tree)}
                              aria-label="View Branch Details"
                              title="View Branch Details"
                            >
                              <Eye className="w-3 h-3" />
                            </ShimmerButton>
                            {(tree.git_branch_name || tree.name) !== 'main' && (
                              <ShimmerButton 
                                size="icon" 
                                variant="ghost" 
                                className="h-6 w-6"
                                onClick={() => setShowDeleteBranch({ project, branch: tree })}
                                disabled={deletingBranches.has(tree.id)}
                                aria-label={deletingBranches.has(tree.id) ? "Deleting Branch..." : "Delete Branch"}
                              >
                                {deletingBranches.has(tree.id) ? (
                                  <div className="animate-spin h-3 w-3 border-2 border-destructive border-t-transparent rounded-full" />
                                ) : (
                                  <Trash2 className="w-3 h-3 text-destructive" />
                                )}
                              </ShimmerButton>
                            )}
                          </div>
                        </div>
                      </li>
                    ))
                  ) : null}
                </ul>
            </li>
          ))}
        </ul>
      )}
      {/* Dialogs */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">New Project</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Project name"
              value={form.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
              autoFocus
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, description: e.target.value }))}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={() => setShowCreate(false)} size="sm">Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={handleCreate} disabled={!form.name.trim()} size="sm">
              Create
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!showCreateBranch} onOpenChange={(v) => !v && setShowCreateBranch(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">New Branch in {showCreateBranch?.name}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Branch name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              autoFocus
              disabled={saving}
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              disabled={saving}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={() => setShowCreateBranch(null)} disabled={saving} size="sm">Cancel</ShimmerButton>
            <ShimmerButton onClick={handleCreateBranch} disabled={saving || !form.name.trim()} size="sm">
              {saving ? "Creating..." : "Create"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!showEdit} onOpenChange={(v: boolean) => { if (!v) setShowEdit(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Edit Project</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Project name"
              value={form.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
              autoFocus
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, description: e.target.value }))}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={() => setShowEdit(null)} size="sm">Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={handleEdit} disabled={!form.name.trim()} size="sm">
              Save
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!showDelete} onOpenChange={(v: boolean) => { if (!v) setShowDelete(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Delete Project</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm">Are you sure you want to delete the project <strong>{showDelete?.name}</strong>?</p>
            {showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs).length > 1 && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                ⚠️ This project has {Object.keys(showDelete.git_branchs).length} branches. You must delete all branches except "main" before deleting the project.
              </p>
            )}
            {showDelete && showDelete.git_branchs && (() => {
              const totalTasks = Object.values(showDelete.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0);
              return totalTasks > 0 ? (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  ⚠️ This project contains {totalTasks} task{totalTasks === 1 ? '' : 's'}. All tasks must be deleted first.
                </p>
              ) : null;
            })()}
            <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={() => setShowDelete(null)} size="sm">Cancel</ShimmerButton>
            <ShimmerButton 
              variant={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs).length > 1) ||
                (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0) > 0)
                  ? "secondary" 
                  : "destructive"
              }
              onClick={handleDelete} 
              size="sm" 
              disabled={
                saving || 
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs).length > 1) ||
                (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0) > 0)
              }
              title={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs).length > 1) 
                  ? "Delete all branches except 'main' first" 
                  : (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0) > 0)
                    ? "Delete all tasks first"
                    : undefined
              }
              className={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs).length > 1) ||
                (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs).reduce((sum, branch: any) => sum + (branch.task_count || 0), 0) > 0)
                  ? "opacity-50 cursor-not-allowed" 
                  : ""
              }
            >
              {saving ? "Deleting..." : "Delete Project"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Branch Dialog */}
      <Dialog open={!!showDeleteBranch} onOpenChange={(v: boolean) => { if (!v) setShowDeleteBranch(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Delete Branch</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm">Are you sure you want to delete the branch <strong>{showDeleteBranch?.branch.git_branch_name || showDeleteBranch?.branch.name}</strong> from project <strong>{showDeleteBranch?.project.name}</strong>?</p>
            {showDeleteBranch && (showDeleteBranch.branch.task_count || 0) > 0 && (
              <p className="text-sm text-destructive">
                Warning: This branch contains {showDeleteBranch.branch.task_count || 0} task(s) that will also be deleted.
              </p>
            )}
            <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={() => setShowDeleteBranch(null)} size="sm" disabled={saving}>
              Cancel
            </ShimmerButton>
            <ShimmerButton 
              variant="destructive" 
              onClick={handleDeleteBranch} 
              size="sm"
              disabled={saving}
            >
              {saving ? "Deleting..." : "Delete Branch"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>



    </div>
  );
};

export default ProjectList; 