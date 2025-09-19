import { Check, Eye, Pencil, Plus, Trash2 } from "lucide-react";
import React, { useEffect, useState, useCallback, useMemo, lazy, Suspense, useRef } from "react";
import { deleteSubtask, listSubtasks, Subtask } from "../api";
import { getSubtaskSummaries } from "../api-lazy";
import { useEntityChanges } from "../hooks/useChangeSubscription";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ShimmerButton } from "./ui/shimmer-button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import SubtaskRow from "./SubtaskRow";

// Lazy load dialogs
const DeleteConfirmDialog = lazy(() => import("./DeleteConfirmDialog"));
const SubtaskCompleteDialog = lazy(() => import("./SubtaskCompleteDialog"));
const SubtaskDetailsDialog = lazy(() => import("./SubtaskDetailsDialog"));
// Import SubtaskCreateDialog directly without lazy loading
import SubtaskCreateDialog from "./SubtaskCreateDialog";
const AgentInfoDialog = lazy(() => import("./AgentInfoDialog"));

interface LazySubtaskListProps {
  projectId: string;
  taskTreeId: string;
  parentTaskId: string;
}

// Lightweight subtask summary for performance
interface SubtaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignees_count: number;
  assignees?: string[]; // Add full assignee information
  progress_percentage?: number;
}

const statusColor: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  done: "default",
  in_progress: "secondary",
  review: "secondary", 
  testing: "secondary",
  todo: "outline",
  blocked: "destructive",
  cancelled: "destructive",
  archived: "outline"
};

const priorityColor: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  low: "outline",
  medium: "secondary",
  high: "default",
  urgent: "destructive"
};

export default function LazySubtaskList({ projectId, taskTreeId, parentTaskId }: LazySubtaskListProps) {
  // Lightweight state for performance
  const [subtaskSummaries, setSubtaskSummaries] = useState<SubtaskSummary[]>([]);
  const [fullSubtasks, setFullSubtasks] = useState<Map<string, Subtask>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingSubtasks, setLoadingSubtasks] = useState<Set<string>>(new Set());
  
  // Only load when component is actually rendered (lazy)
  const [hasLoaded, setHasLoaded] = useState(false);

  // Track previous subtask IDs for detecting new subtasks
  const [previousSubtaskIds, setPreviousSubtaskIds] = useState<Set<string>>(new Set());

  // Row animation callback registry
  const rowAnimationCallbacks = useRef<Map<string, {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }>>(new Map());

  // Dialog states
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; subtaskId: string | null }>({
    open: false,
    subtaskId: null
  });
  
  const [activeDialog, setActiveDialog] = useState<{
    type: 'details' | 'edit' | 'complete' | null;
    subtaskId?: string;
    subtask?: Subtask | null;
  }>({ type: null });
  
  const [detailsDialog, setDetailsDialog] = useState<{
    open: boolean;
    subtask: Subtask | null;
  }>({ open: false, subtask: null });
  
  const [editingSubtask, setEditingSubtask] = useState<Subtask | null>(null);
  const [showDetails, setShowDetails] = useState<string | null>(null);
  
  // Agent info dialog state
  const [selectedAgentForInfo, setSelectedAgentForInfo] = useState<string | null>(null);
  const [agentInfoDialogOpen, setAgentInfoDialogOpen] = useState(false);

  // Create subtask dialog state
  const [createSubtaskDialogOpen, setCreateSubtaskDialogOpen] = useState(false);



  // Handle agent info click
  const handleAgentInfoClick = (agentName: string) => {
    setSelectedAgentForInfo(agentName);
    setAgentInfoDialogOpen(true);
  };

  // Handle opening create subtask dialog
  const handleOpenCreateSubtask = useCallback(() => {
    setCreateSubtaskDialogOpen(true);
  }, []);

  // Handle subtask creation
  const handleSubtaskCreated = useCallback((newSubtask: Subtask) => {

    // Add to summaries
    const newSummary: SubtaskSummary = {
      id: newSubtask.id,
      title: newSubtask.title,
      status: newSubtask.status,
      priority: newSubtask.priority,
      assignees_count: newSubtask.assignees?.length || 0,
      assignees: newSubtask.assignees,
      progress_percentage: newSubtask.progress_percentage
    };

    setSubtaskSummaries(prev => [...prev, newSummary]);

    // Add to full subtasks
    setFullSubtasks(prev => {
      const newMap = new Map(prev);
      newMap.set(newSubtask.id, newSubtask);
      return newMap;
    });

    // Ensure dialog is closed
    setCreateSubtaskDialogOpen(false);
  }, []);

  // Load full subtasks fallback
  const loadFullSubtasksFallback = useCallback(async () => {
    try {
      const subtasks = await listSubtasks(parentTaskId);

      // Convert to summaries
      const summaries: SubtaskSummary[] = subtasks.map(subtask => ({
        id: subtask.id,
        title: subtask.title,
        status: subtask.status,
        priority: subtask.priority,
        assignees_count: subtask.assignees?.length || 0,
        assignees: subtask.assignees, // Include full assignee information
        progress_percentage: subtask.progress_percentage
      }));

      setSubtaskSummaries(summaries);

      // Store full subtasks for immediate access
      const subtaskMap = new Map();
      subtasks.forEach(subtask => subtaskMap.set(subtask.id, subtask));
      setFullSubtasks(subtaskMap);

    } catch (e: any) {
      setError(e.message);
    }
  }, [parentTaskId]);

  // Load subtask summaries (lightweight)
  const loadSubtaskSummaries = useCallback(async () => {
    if (hasLoaded) return; // Only load once

    setLoading(true);
    setError(null);

    try {
      // Use the proper API function that handles authentication and proper URLs
      const data = await getSubtaskSummaries(parentTaskId);
      setSubtaskSummaries(data.subtasks);

    } catch (e) {
      console.warn('Lightweight subtask endpoint not available, falling back');
      await loadFullSubtasksFallback();
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  }, [parentTaskId, hasLoaded, loadFullSubtasksFallback]);

  // Register row animation callbacks
  const registerRowCallbacks = useCallback((subtaskId: string, callbacks: {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }) => {
    rowAnimationCallbacks.current.set(subtaskId, callbacks);
  }, []);

  // Unregister row callbacks
  const unregisterRowCallbacks = useCallback((subtaskId: string) => {
    rowAnimationCallbacks.current.delete(subtaskId);
  }, []);

  // Stable refresh callback for changePoolService
  const handleSubtaskChanges = useCallback(async () => {
    console.log('📡 LazySubtaskList: Subtask changes detected, refreshing...');

    // Store current subtask IDs and data before refresh for comparison
    const currentSubtaskIds = new Set(subtaskSummaries.map(s => s.id));
    const currentSubtaskMap = new Map(subtaskSummaries.map(s => [s.id, s]));

    // Force reload of subtasks for this parent task
    setHasLoaded(false); // Reset loaded flag to trigger refresh

    try {
      // Use the proper API function that handles authentication and proper URLs
      const data = await getSubtaskSummaries(parentTaskId);
      const newSummaries = data.subtasks;
      const newSubtaskIds = new Set(newSummaries.map(s => s.id));

      // Detect changes and trigger animations
      // 1. New subtasks (created) - only if we have a previous state to compare
      if (currentSubtaskIds.size > 0) {
        const addedSubtasks = new Set([...newSubtaskIds].filter(id => !currentSubtaskIds.has(id)));
        console.log('🔍 Subtask change detection - currentSubtaskIds:', currentSubtaskIds.size, 'newSubtaskIds:', newSubtaskIds.size, 'addedSubtasks:', addedSubtasks.size);

        if (addedSubtasks.size > 0) {
          console.log('✨ New subtasks detected:', [...addedSubtasks]);
          // Wait a bit for SubtaskRow to register callbacks
          setTimeout(() => {
            addedSubtasks.forEach(subtaskId => {
              const callbacks = rowAnimationCallbacks.current.get(subtaskId);
              if (callbacks) {
                console.log('🎬 Playing create animation for subtask:', subtaskId);
                callbacks.playCreateAnimation();
              } else {
                console.warn('⚠️ No callbacks found for subtask:', subtaskId);
              }
            });
          }, 100);
        }
      } else {
        console.log('🏁 Initial subtask load - no animation for existing subtasks');
      }

      // 2. Removed subtasks (deleted) - need to keep them in the list during animation
      const removedSubtasks = new Set([...currentSubtaskIds].filter(id => !newSubtaskIds.has(id)));
      if (removedSubtasks.size > 0) {
        console.log('🗑️ Deleted subtasks detected:', [...removedSubtasks]);

        // Add deleted subtasks back to the summaries temporarily for animation
        const deletedSubtasksData = subtaskSummaries.filter(subtask => removedSubtasks.has(subtask.id));
        newSummaries.push(...deletedSubtasksData);

        removedSubtasks.forEach(subtaskId => {
          const callbacks = rowAnimationCallbacks.current.get(subtaskId);
          if (callbacks) {
            console.log('🎬 Playing delete animation for subtask:', subtaskId);
            callbacks.playDeleteAnimation();
          } else {
            console.warn('⚠️ No callbacks found for deleted subtask:', subtaskId);
          }
        });
      }

      // 3. Updated subtasks (modified)
      const updatedSubtasks = new Set();
      newSummaries.forEach(newSubtask => {
        const oldSubtask = currentSubtaskMap.get(newSubtask.id);
        if (oldSubtask && (
          oldSubtask.title !== newSubtask.title ||
          oldSubtask.status !== newSubtask.status ||
          oldSubtask.priority !== newSubtask.priority ||
          oldSubtask.progress_percentage !== newSubtask.progress_percentage ||
          (oldSubtask.assignees && newSubtask.assignees && oldSubtask.assignees.length !== newSubtask.assignees.length)
        )) {
          updatedSubtasks.add(newSubtask.id);
        }
      });
      updatedSubtasks.forEach(subtaskId => {
        const callbacks = rowAnimationCallbacks.current.get(subtaskId as string);
        if (callbacks) {
          console.log('🎬 Playing update animation for subtask:', subtaskId);
          callbacks.playUpdateAnimation();
        }
      });

      // Update states
      setSubtaskSummaries(newSummaries);
      setPreviousSubtaskIds(newSubtaskIds);

    } catch (e) {
      console.warn('Lightweight subtask endpoint not available, falling back');
      await loadFullSubtasksFallback();
    } finally {
      setHasLoaded(true);
    }
  }, [subtaskSummaries, parentTaskId, loadFullSubtasksFallback]);

  // Subscribe to centralized change pool for real-time updates
  // Listen to subtask changes for this specific parent task
  useEntityChanges(
    'LazySubtaskList',
    ['subtask'],
    handleSubtaskChanges,
    {
      branchId: taskTreeId,   // Filter by specific branch
      projectId: projectId,   // Filter by specific project
      entityIds: [parentTaskId] // Listen to changes affecting this parent task
    }
  );


  // Load full subtask data on demand
  const loadFullSubtask = useCallback(async (subtaskId: string): Promise<Subtask | null> => {
    if (fullSubtasks.has(subtaskId)) {
      return fullSubtasks.get(subtaskId) || null;
    }
    
    if (loadingSubtasks.has(subtaskId)) {
      return null; // Already loading
    }
    
    setLoadingSubtasks(prev => {
      const newSet = new Set(prev);
      newSet.add(subtaskId);
      return newSet;
    });
    
    try {
      // For now, load all subtasks since we don't have individual endpoint
      if (fullSubtasks.size === 0) {
        await loadFullSubtasksFallback();
      }
      
      const subtask = fullSubtasks.get(subtaskId) || null;
      
      setLoadingSubtasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(subtaskId);
        return newSet;
      });
      
      return subtask;
      
    } catch (e) {
      console.error(`Failed to load subtask ${subtaskId}:`, e);
      setLoadingSubtasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(subtaskId);
        return newSet;
      });
      return null;
    }
  }, [fullSubtasks, loadingSubtasks, loadFullSubtasksFallback]);

  // Load subtasks when component mounts
  useEffect(() => {
    loadSubtaskSummaries();
  }, [loadSubtaskSummaries]);

  // Delete subtask handler - row animation handled independently
  const handleDeleteSubtask = useCallback(async (subtaskId: string) => {
    // Close dialog immediately for better UX
    setDeleteDialog({ open: false, subtaskId: null });

    try {
      // Call API to delete subtask
      await deleteSubtask(subtaskId);
      // Note: The actual row removal will be handled by WebSocket events and animation system
      // The handleSubtaskChanges function will detect the deletion and trigger the animation
    } catch (error) {
      console.error('Failed to delete subtask:', error);
      // TODO: Show error toast/notification
    }
  }, []);

  // Handle subtask actions - Fixed double-click issue
  const handleSubtaskAction = useCallback((action: 'details' | 'edit' | 'complete', subtaskId: string) => {
    // Get existing subtask data if available
    const existingSubtask = fullSubtasks.get(subtaskId);
    
    // Set dialog state immediately to fix double-click issue
    switch (action) {
      case 'details':
        // Open the details dialog immediately, even with null data
        setDetailsDialog({ open: true, subtask: existingSubtask || null });
        break;
      case 'edit':
        setEditingSubtask(existingSubtask || null);
        break;
      case 'complete':
        setActiveDialog({ type: 'complete', subtaskId, subtask: existingSubtask || null });
        break;
    }
    
    // Load full subtask data asynchronously after dialog is opened
    if (!existingSubtask) {
      loadFullSubtask(subtaskId).then(subtask => {
        if (subtask) {
          switch (action) {
            case 'details':
              setDetailsDialog({ open: true, subtask });
              break;
            case 'edit':
              setEditingSubtask(subtask);
              break;
            case 'complete':
              setActiveDialog({ type: 'complete', subtaskId, subtask });
              break;
          }
        }
      }).catch(error => {
        console.error('Failed to load subtask for action:', action, error);
      });
    }
  }, [loadFullSubtask, fullSubtasks]);

  // Handle subtask completion
  const handleCompleteSubtask = useCallback((completedSubtask: Subtask) => {
    // Update summaries
    setSubtaskSummaries(prev => prev.map(s => 
      s.id === completedSubtask.id 
        ? { ...s, status: 'done' }
        : s
    ));
    
    // Update full subtasks
    setFullSubtasks(prev => {
      const newMap = new Map(prev);
      newMap.set(completedSubtask.id, completedSubtask);
      return newMap;
    });
    
    setActiveDialog({ type: null });
  }, []);

  // Memoized progress calculation - Force 100% for done subtasks
  const progressSummary = useMemo(() => {
    if (subtaskSummaries.length === 0) return null;
    
    const total = subtaskSummaries.length;
    const completed = subtaskSummaries.filter(s => s.status === 'done').length;
    const inProgress = subtaskSummaries.filter(s => s.status === 'in_progress').length;
    
    return {
      total,
      completed,
      inProgress,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0
    };
  }, [subtaskSummaries]);

  // Render subtask row using new SubtaskRow component
  const renderSubtaskRow = useCallback((summary: SubtaskSummary) => {
    const isLoadingFull = loadingSubtasks.has(summary.id);
    const isShowingDetails = showDetails === summary.id;
    const fullSubtask = fullSubtasks.get(summary.id);

    return (
      <SubtaskRow
        key={summary.id}
        summary={summary}
        fullSubtask={fullSubtask || null}
        isLoading={isLoadingFull}
        showDetails={isShowingDetails}
        onPlayCreateAnimation={() => {}}
        onPlayDeleteAnimation={() => {}}
        onPlayUpdateAnimation={() => {}}
        onSubtaskAction={handleSubtaskAction}
        onAgentInfoClick={handleAgentInfoClick}
        onDeleteSubtask={(subtaskId) => setDeleteDialog({ open: true, subtaskId })}
        onRegisterCallbacks={registerRowCallbacks}
        onUnregisterCallbacks={unregisterRowCallbacks}
      />
    );
  }, [
    loadingSubtasks,
    fullSubtasks,
    showDetails,
    handleSubtaskAction,
    handleAgentInfoClick,
    registerRowCallbacks,
    unregisterRowCallbacks
  ]);

  if (loading) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        Loading subtasks...
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="p-4 text-center text-sm text-red-500">
        Error loading subtasks: {error}
      </div>
    );
  }
  
  if (subtaskSummaries.length === 0) {
    return (
      <div className="p-6 bg-gradient-to-r from-blue-50/30 to-transparent dark:from-blue-950/20 dark:to-transparent">

        <div className="flex items-center gap-2 mb-4">
          <div className="h-px flex-1 bg-gradient-to-r from-blue-300 to-transparent dark:from-blue-700"></div>
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">Subtasks</span>
          <div className="h-px flex-1 bg-gradient-to-l from-blue-300 to-transparent dark:from-blue-700"></div>
        </div>
        <div className="text-center text-sm text-blue-600/70 dark:text-blue-400/70 py-4">
          <div className="mb-3">No subtasks found.</div>
          <Button
            variant="outline"
            size="sm"
            className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 border-blue-300 hover:bg-blue-50 dark:border-blue-700 dark:hover:bg-blue-950/50 relative z-20"
            onClick={() => {
              handleOpenCreateSubtask();
            }}
          >
            <Plus className="w-3 h-3 mr-1" />
            Add Subtask
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 p-4 bg-gradient-to-r from-blue-50/30 to-transparent dark:from-blue-950/20 dark:to-transparent">

      {/* Subtask Section Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="h-px flex-1 bg-gradient-to-r from-blue-300 to-transparent dark:from-blue-700"></div>
        <span className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">Subtasks</span>
        <div className="h-px flex-1 bg-gradient-to-l from-blue-300 to-transparent dark:from-blue-700"></div>
      </div>
      
      {/* Progress Summary */}
      {progressSummary && (
        <div className="flex items-center gap-4 p-3 bg-white/70 dark:bg-gray-800/70 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="text-sm">
            <strong className="text-blue-700 dark:text-blue-300">Progress:</strong> {progressSummary.completed}/{progressSummary.total} completed ({progressSummary.percentage}%)
          </div>
          {progressSummary.inProgress > 0 && (
            <Badge variant="secondary" className="text-xs">
              {progressSummary.inProgress} in progress
            </Badge>
          )}
          <div className="flex-1">
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="h-2 rounded-full transition-all duration-300 relative overflow-hidden group"
                style={{ width: `${progressSummary.percentage}%` }}
              >
                {/* Background gradient - lighter blue for subtasks */}
                <div className="absolute inset-0 bg-gradient-to-r from-blue-300 to-blue-500" />
                
                {/* Animated shimmer overlay */}
                <div 
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  style={{
                    backgroundSize: '200% 100%',
                    animation: 'shimmer-progress 2s infinite linear'
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Subtasks Table */}
      <Table className="bg-white/50 dark:bg-gray-900/50 rounded-lg overflow-hidden">
        <TableHeader>
          <TableRow className="bg-gray-100/50 dark:bg-gray-800/20 border-b border-gray-200 dark:border-gray-700">
            <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">Subtask</TableHead>
            <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">Status</TableHead>
            <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">Priority</TableHead>
            <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">Assignees</TableHead>
            <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {subtaskSummaries.map(renderSubtaskRow)}
        </TableBody>
      </Table>
      
      {/* Add Subtask Button */}
      <div className="flex justify-end pt-2 border-t border-blue-200/50 dark:border-blue-800/50">
        <Button
          variant="outline"
          size="sm"
          className="mt-2 border-blue-300 text-blue-600 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-400 dark:hover:bg-blue-950/50 relative z-20"
          onClick={handleOpenCreateSubtask}
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Subtask
        </Button>
      </div>
      
      {/* Create Subtask Dialog - Not lazy loaded */}
      <SubtaskCreateDialog
        open={createSubtaskDialogOpen}
        onOpenChange={setCreateSubtaskDialogOpen}
        parentTaskId={parentTaskId}
        onClose={() => setCreateSubtaskDialogOpen(false)}
        onCreated={handleSubtaskCreated}
      />

      {/* Dialogs */}
      <Suspense fallback={null}>
        {/* Delete Confirmation Dialog */}
        {deleteDialog.open && deleteDialog.subtaskId && (
          <DeleteConfirmDialog
            open={deleteDialog.open}
            onOpenChange={(open) => setDeleteDialog({ open, subtaskId: null })}
            onConfirm={() => deleteDialog.subtaskId && handleDeleteSubtask(deleteDialog.subtaskId)}
            title="Delete Subtask"
            description="Are you sure you want to delete this subtask? This action cannot be undone."
            itemName={subtaskSummaries.find(s => s.id === deleteDialog.subtaskId)?.title}
          />
        )}

        {/* Complete Subtask Dialog */}
        {activeDialog.type === 'complete' && activeDialog.subtask && (
          <SubtaskCompleteDialog
            open={true}
            onOpenChange={(open) => !open && setActiveDialog({ type: null })}
            subtask={activeDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={() => setActiveDialog({ type: null })}
            onComplete={handleCompleteSubtask}
          />
        )}
        
        {/* TODO: Add Edit Dialog when SubtaskEditDialog component is available */}
        {editingSubtask && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-md w-full">
              <h3 className="text-lg font-semibold mb-4">Edit Subtask</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Editing: {editingSubtask.title}
              </p>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setEditingSubtask(null)}>
                  Cancel
                </Button>
                <Button onClick={() => {
                  // TODO: Implement save functionality
                  setEditingSubtask(null);
                }}>
                  Save Changes
                </Button>
              </div>
            </div>
          </div>
        )}
      </Suspense>
      
      {/* Subtask Details Dialog */}
      <Suspense fallback={null}>
        {detailsDialog.subtask && (
          <SubtaskDetailsDialog
            open={detailsDialog.open}
            onOpenChange={(open) => setDetailsDialog({ open, subtask: detailsDialog.subtask })}
            subtask={detailsDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={() => setDetailsDialog({ open: false, subtask: null })}
          />
        )}
      </Suspense>
      
      {/* Agent Info Dialog */}
      <Suspense fallback={null}>
        {selectedAgentForInfo && (
          <AgentInfoDialog
            open={agentInfoDialogOpen}
            onOpenChange={setAgentInfoDialogOpen}
            agentName={selectedAgentForInfo}
            taskTitle={`Subtask: ${subtaskSummaries.find(s => s.assignees?.includes(selectedAgentForInfo))?.title || ''}`}
            onClose={() => {
              setAgentInfoDialogOpen(false);
              setSelectedAgentForInfo(null);
            }}
          />
        )}
      </Suspense>
    </div>
  );
}