import { Check, Eye, Pencil, Plus, Trash2 } from "lucide-react";
import React, { useEffect, useState, useCallback, useMemo, lazy, Suspense } from "react";
import { deleteSubtask, listSubtasks, Subtask } from "../api";
import { getSubtaskSummaries } from "../api-lazy";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ShimmerButton } from "./ui/shimmer-button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";

// Lazy load dialogs
const DeleteConfirmDialog = lazy(() => import("./DeleteConfirmDialog"));
const SubtaskCompleteDialog = lazy(() => import("./SubtaskCompleteDialog"));

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
  
  const [editingSubtask, setEditingSubtask] = useState<Subtask | null>(null);
  const [showDetails, setShowDetails] = useState<string | null>(null);

  // Fallback to current implementation
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

  // Delete subtask handler
  const handleDeleteSubtask = useCallback(async (subtaskId: string) => {
    try {
      const success = await deleteSubtask(parentTaskId, subtaskId);
      if (success) {
        // Remove from summaries
        setSubtaskSummaries(prev => prev.filter(s => s.id !== subtaskId));
        // Remove from full subtasks
        setFullSubtasks(prev => {
          const newMap = new Map(prev);
          newMap.delete(subtaskId);
          return newMap;
        });
      }
    } catch (error) {
      console.error('Failed to delete subtask:', error);
    }
    setDeleteDialog({ open: false, subtaskId: null });
  }, [parentTaskId]);

  // Handle subtask actions
  const handleSubtaskAction = useCallback(async (action: 'details' | 'edit' | 'complete', subtaskId: string) => {
    // Load full subtask data if not already loaded
    const subtask = await loadFullSubtask(subtaskId);
    
    if (!subtask) {
      console.error('Failed to load subtask for action:', action);
      return;
    }
    
    switch (action) {
      case 'details':
        setShowDetails(showDetails === subtaskId ? null : subtaskId);
        break;
      case 'edit':
        setEditingSubtask(subtask);
        break;
      case 'complete':
        setActiveDialog({ type: 'complete', subtaskId, subtask });
        break;
    }
  }, [loadFullSubtask, showDetails]);

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

  // Memoized progress calculation
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

  // Render subtask row
  const renderSubtaskRow = useCallback((summary: SubtaskSummary) => {
    const isLoadingFull = loadingSubtasks.has(summary.id);
    const isShowingDetails = showDetails === summary.id;
    const fullSubtask = fullSubtasks.get(summary.id);
    
    return (
      <React.Fragment key={summary.id}>
        <TableRow className="text-sm hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
          <TableCell className="pl-8">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-400 dark:bg-blue-600"></div>
              <span className="text-gray-700 dark:text-gray-300">{summary.title}</span>
              {summary.progress_percentage !== undefined && (
                <Badge variant="outline" className="text-xs bg-gray-100 dark:bg-gray-800/50 border-gray-300 dark:border-gray-700">
                  {summary.progress_percentage}%
                </Badge>
              )}
            </div>
          </TableCell>
          
          <TableCell>
            <HolographicStatusBadge status={summary.status as any} size="xs" />
          </TableCell>
          
          <TableCell>
            <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
          </TableCell>
          
          <TableCell>
            {summary.assignees_count > 0 ? (
              <Badge variant="secondary" className="text-xs">
                {summary.assignees_count} assigned
              </Badge>
            ) : (
              <span className="text-xs text-muted-foreground">Unassigned</span>
            )}
          </TableCell>
          
          <TableCell>
            <div className="flex gap-1">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => handleSubtaskAction('details', summary.id)}
                disabled={isLoadingFull}
                title="View details"
              >
                {isLoadingFull ? (
                  <div className="w-3 h-3 border border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                ) : (
                  <Eye className="w-3 h-3" />
                )}
              </Button>
              
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => handleSubtaskAction('edit', summary.id)}
                disabled={isLoadingFull || summary.status === 'done'}
                title="Edit"
              >
                <Pencil className="w-3 h-3" />
              </Button>
              
              {summary.status !== 'done' && (
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => handleSubtaskAction('complete', summary.id)}
                  disabled={isLoadingFull}
                  title="Complete"
                >
                  <Check className="w-3 h-3" />
                </Button>
              )}
              
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setDeleteDialog({ open: true, subtaskId: summary.id })}
                title="Delete subtask"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
        
        {/* Subtask Details Row */}
        {isShowingDetails && fullSubtask && (
          <TableRow className="bg-blue-50/30 dark:bg-blue-950/10">
            <TableCell colSpan={5} className="pl-12">
              <div className="py-2 space-y-2">
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  <strong>Description:</strong> {fullSubtask.description || 'No description'}
                </div>
                {fullSubtask.assignees && fullSubtask.assignees.length > 0 && (
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <strong>Assignees:</strong> {fullSubtask.assignees.join(', ')}
                  </div>
                )}
                {fullSubtask.progress_notes && (
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <strong>Progress Notes:</strong> {fullSubtask.progress_notes}
                  </div>
                )}
              </div>
            </TableCell>
          </TableRow>
        )}
      </React.Fragment>
    );
  }, [loadingSubtasks, fullSubtasks, showDetails, handleSubtaskAction]);

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
          No subtasks found.
          <Button 
            variant="ghost" 
            size="sm" 
            className="ml-2 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            onClick={() => {/* TODO: Open create subtask dialog */}}
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
                {/* Background gradient */}
                <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-blue-600" />
                
                {/* Animated shimmer overlay */}
                <div 
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
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
          className="mt-2 border-blue-300 text-blue-600 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-400 dark:hover:bg-blue-950/50"
          onClick={() => {/* TODO: Open create subtask dialog */}}
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Subtask
        </Button>
      </div>
      
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
    </div>
  );
}