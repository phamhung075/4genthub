import { Check, Eye, Pencil, Plus, Trash2 } from "lucide-react";
import React, { useEffect, useState, useCallback, useMemo, lazy, Suspense, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { deleteSubtask, getSubtask, listSubtasks, Subtask } from "../api";
import { getSubtaskSummaries, SubtaskSummary } from "../api-lazy";
import { useChangeSubscription } from "../hooks/useChangeSubscription";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import SubtaskRow from "./SubtaskRow";
import logger from "../utils/logger";

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

// Using SubtaskSummary interface from api-lazy.ts

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
  // URL parameter monitoring
  const { subtaskId, taskId } = useParams<{ subtaskId?: string, taskId?: string }>();
  const navigate = useNavigate();

  // Lightweight state for performance
  const [subtaskSummaries, setSubtaskSummaries] = useState<SubtaskSummary[]>([]);
  const [fullSubtasks, setFullSubtasks] = useState<Map<string, Subtask>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingSubtasks, setLoadingSubtasks] = useState<Set<string>>(new Set());
  
  // Only load when component is actually rendered (lazy)
  const [hasLoaded, setHasLoaded] = useState(false);
  // Separate flag to control subscription timing - prevents race conditions
  const [subscriptionEnabled, setSubscriptionEnabled] = useState(false);

  // Track previous subtask IDs for detecting new subtasks
  const [previousSubtaskIds, setPreviousSubtaskIds] = useState<Set<string>>(new Set());

  // Track previous subtasks for change detection and animation triggering
  const previousSubtasksRef = useRef<Map<string, SubtaskSummary>>(new Map());
  const [animationTriggers, setAnimationTriggers] = useState<{
    created: Set<string>;
    updated: Set<string>;
    deleted: Set<string>;
  }>({ created: new Set(), updated: new Set(), deleted: new Set() });

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

  // Track when we're programmatically opening a dialog to prevent race conditions
  const [isOpeningDialog, setIsOpeningDialog] = useState(false);
  
  const [editingSubtask, setEditingSubtask] = useState<Subtask | null>(null);
  const [showDetails, setShowDetails] = useState<string | null>(null);
  
  // Agent info dialog state
  const [selectedAgentForInfo, setSelectedAgentForInfo] = useState<string | null>(null);
  const [agentInfoDialogOpen, setAgentInfoDialogOpen] = useState(false);

  // Create subtask dialog state
  const [createSubtaskDialogOpen, setCreateSubtaskDialogOpen] = useState(false);

  // Handle subtask dialog close - remove subtaskId from URL
  const handleSubtaskDialogClose = useCallback(() => {
    const taskUrl = `/dashboard/project/${projectId}/branch/${taskTreeId}/task/${parentTaskId}`;
    navigate(taskUrl);
  }, [navigate, projectId, taskTreeId, parentTaskId]);



  // Handle agent info click
  const handleAgentInfoClick = (agentName: string) => {
    logger.debug('🎯 Agent info clicked:', agentName);
    logger.debug('📋 Current subtask summaries:', subtaskSummaries);
    logger.debug('👥 All assignees:', subtaskSummaries.map(s => s.assignees));
    setSelectedAgentForInfo(agentName);
    setAgentInfoDialogOpen(true);
    logger.debug('🔓 Dialog state after click:', {
      agent: agentName,
      dialogOpen: true
    });
  };

  // Handle opening create subtask dialog
  const handleOpenCreateSubtask = useCallback(() => {
    logger.debug('🎬 handleOpenCreateSubtask called');
    setCreateSubtaskDialogOpen(true);
    logger.debug('✅ Dialog state set to open');
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
      // Silently handle 400 errors for non-existent tasks
      if (e.status === 400 || e.response?.status === 400) {
        // Task might not exist or have been deleted, just show empty subtasks
        setSubtaskSummaries([]);
        setFullSubtasks(new Map());
      } else {
        setError(e.message);
      }
    }
  }, [parentTaskId]);

  // Load subtask summaries (lightweight) with request deduplication
  const loadSubtaskSummaries = useCallback(async () => {
    if (hasLoaded) return; // Only load once

    setLoading(true);
    setError(null);

    try {
      // Use the proper API function that handles authentication and proper URLs
      const data = await getSubtaskSummaries(parentTaskId);
      setSubtaskSummaries(data.subtasks);

    } catch (e: any) {
      // Only log warning for non-400 errors
      if (e.status !== 400 && e.response?.status !== 400) {
        logger.warn('Lightweight subtask endpoint not available, falling back');
      }
      await loadFullSubtasksFallback();
    } finally {
      setLoading(false);
      setHasLoaded(true);

      // Enable subscription AFTER initial load is complete
      // Use setTimeout to ensure state has settled before enabling subscription
      setTimeout(() => {
        setSubscriptionEnabled(true);
        logger.debug(`📡 LazySubtaskList-${parentTaskId}: Subscription enabled after initial load`);
      }, 250); // Small delay to prevent race conditions
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

  // Debounce timer ref for batching rapid changes
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Stable refresh callback for changePoolService with enhanced protection
  const handleSubtaskChanges = useCallback(async () => {
    // PERFORMANCE FIX: Skip refresh during initial load to prevent duplicate API calls
    if (!hasLoaded || !subscriptionEnabled) {
      console.log(`📡 LazySubtaskList-${parentTaskId}: Skipping refresh - hasLoaded:${hasLoaded}, subscriptionEnabled:${subscriptionEnabled}`);
      return;
    }

    // Clear existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Debounce rapid changes to prevent multiple API calls
    debounceTimerRef.current = setTimeout(async () => {
      console.log(`📡 LazySubtaskList-${parentTaskId}: Subtask changes detected, refreshing...`);
      logger.debug('📡 LazySubtaskList: Subtask changes detected, refreshing...');

    // Store current subtask data for comparison
    const currentSubtaskMap = new Map(subtaskSummaries.map(s => [s.id, s]));
    const currentSubtaskIds = new Set(subtaskSummaries.map(s => s.id));

    // Force reload of subtasks for this parent task
    // Note: No need to reset hasLoaded flag - we're refreshing data directly via API call

    try {
      // Use the proper API function that handles authentication and proper URLs
      const data = await getSubtaskSummaries(parentTaskId);
      const newSummaries = data.subtasks;
      const newSubtaskIds = new Set(newSummaries.map(s => s.id));

      // Detect changes for animation triggering
      const newAnimationTriggers = {
        created: new Set<string>(),
        updated: new Set<string>(),
        deleted: new Set<string>()
      };

      // 1. New subtasks (created) - only if we have a previous state to compare
      if (currentSubtaskIds.size > 0) {
        const addedSubtasks = [...newSubtaskIds].filter(id => !currentSubtaskIds.has(id));
        logger.debug('🔍 Subtask change detection', { currentSubtaskIds: currentSubtaskIds.size, newSubtaskIds: newSubtaskIds.size, addedSubtasks: addedSubtasks.length });

        if (addedSubtasks.length > 0) {
          logger.debug('✨ New subtasks detected:', addedSubtasks);
          addedSubtasks.forEach(subtaskId => newAnimationTriggers.created.add(subtaskId));
        }
      } else {
        logger.debug('🏁 Initial subtask load - no animation for existing subtasks');
      }

      // 2. Removed subtasks (deleted) - need to keep them in the list during animation
      const removedSubtasks = [...currentSubtaskIds].filter(id => !newSubtaskIds.has(id));
      if (removedSubtasks.length > 0) {
        logger.debug('🗑️ Deleted subtasks detected:', removedSubtasks);

        // Add deleted subtasks back to the summaries temporarily for animation
        const deletedSubtasksData = subtaskSummaries.filter(subtask => removedSubtasks.includes(subtask.id));
        newSummaries.push(...deletedSubtasksData);

        removedSubtasks.forEach(subtaskId => newAnimationTriggers.deleted.add(subtaskId));
      }

      // 3. Updated subtasks (modified)
      newSummaries.forEach(newSubtask => {
        const oldSubtask = currentSubtaskMap.get(newSubtask.id);
        if (oldSubtask && (
          oldSubtask.title !== newSubtask.title ||
          oldSubtask.status !== newSubtask.status ||
          oldSubtask.priority !== newSubtask.priority ||
          oldSubtask.progress_percentage !== newSubtask.progress_percentage ||
          (oldSubtask.assignees && newSubtask.assignees && oldSubtask.assignees.length !== newSubtask.assignees.length)
        )) {
          logger.debug('🔄 Updated subtask detected:', newSubtask.id);
          newAnimationTriggers.updated.add(newSubtask.id);
        }
      });

      // Update previous subtasks reference for next comparison
      previousSubtasksRef.current = new Map(newSummaries.map(s => [s.id, s]));

      // Update states
      setSubtaskSummaries(newSummaries);
      setPreviousSubtaskIds(newSubtaskIds);

      // Set animation triggers to trigger animations in useEffect
      if (newAnimationTriggers.created.size > 0 ||
          newAnimationTriggers.updated.size > 0 ||
          newAnimationTriggers.deleted.size > 0) {
        setAnimationTriggers(newAnimationTriggers);
      }

    } catch (e: any) {
      // Only log warning for non-400 errors
      if (e.status !== 400 && e.response?.status !== 400) {
        logger.warn('Lightweight subtask endpoint not available, falling back');
      }
      await loadFullSubtasksFallback();
    } finally {
      setHasLoaded(true);
    }
    }, 200); // 200ms debounce delay to batch rapid changes
  }, [subtaskSummaries, parentTaskId, loadFullSubtasksFallback, hasLoaded, subscriptionEnabled]);

  // Subscribe to centralized change pool for real-time updates
  // Listen to subtask changes for this specific parent task
  // PERFORMANCE FIX: Only enable subscription after initial load to prevent duplicate API calls
  useChangeSubscription({
    componentId: `LazySubtaskList-${parentTaskId}`,
    entityTypes: ['subtask'],
    refreshCallback: handleSubtaskChanges,
    // REMOVED: branchId and projectId filters because subtask notifications don't include these fields
    // branchId: taskTreeId,   // Filter by specific branch
    // projectId: projectId,   // Filter by specific project
    // Custom filter to only refresh when the subtask belongs to this parent task
    shouldRefresh: (notification) => {
      // DEBUG: Log all subtask notifications to see what we're receiving
      console.log(`🔔 LazySubtaskList-${parentTaskId}: Received subtask notification:`, {
        entityType: notification.entityType,
        eventType: notification.eventType,
        entityId: notification.entityId,
        parentTaskId: notification.metadata?.parent_task_id,
        currentParentTaskId: parentTaskId,
        shouldRefresh: notification.metadata?.parent_task_id === parentTaskId
      });

      // Only refresh if the subtask belongs to this parent task
      return notification.metadata?.parent_task_id === parentTaskId;
    },
    // PERFORMANCE FIX: Only enable subscription after initial load completes
    // This prevents the subscription from triggering during initial mount and causing duplicate calls
    enabled: subscriptionEnabled
  });


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
      logger.error(`Failed to load subtask ${subtaskId}:`, e);
      setLoadingSubtasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(subtaskId);
        return newSet;
      });
      return null;
    }
  }, [fullSubtasks, loadingSubtasks, loadFullSubtasksFallback]);

  // Load a specific subtask by ID (cross-component check)
  const loadSubtaskById = useCallback(async (subtaskId: string): Promise<Subtask | null> => {
    try {
      // Validate UUID format before making API call
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(subtaskId)) {
        logger.debug(`Invalid subtask ID format, skipping API call: ${subtaskId}`);
        return null;
      }

      // Use the direct subtask API to get the subtask details
      // Note: parentTaskId is kept for backward compatibility but not used by the API
      const subtask = await getSubtask(parentTaskId, subtaskId);
      // Check if the loaded subtask actually belongs to this parent task
      if (subtask && subtask.parent_task_id === parentTaskId) {
        return subtask;
      }
      logger.debug(`Subtask ${subtaskId} does not belong to parent task ${parentTaskId}`);
      return null;
    } catch (error: any) {
      // Handle 404 and validation errors silently for cross-component checks
      if (error?.name === 'NotFoundError' || error?.status === 404 ||
          error?.message?.includes('Invalid subtask ID format')) {
        logger.debug('Subtask not found or invalid format (cross-component check):', {
          subtaskId,
          parentTaskId,
          errorType: error?.name || 'UNKNOWN'
        });
        return null;
      }

      // Log other errors as debug level to avoid console noise
      logger.debug('Error loading subtask by ID (cross-component check):', {
        error: error?.message || error,
        subtaskId,
        parentTaskId
      });
      return null;
    }
  }, [parentTaskId]);

  // Load subtasks when component mounts
  useEffect(() => {
    loadSubtaskSummaries();
  }, [loadSubtaskSummaries]);

  // Monitor subtaskId URL parameter and auto-open dialog
  useEffect(() => {
    // 🚀 PERFORMANCE FIX: Only react to URL changes if the taskId in URL matches this component's parentTaskId
    // This prevents ALL LazySubtaskList components from reacting to ANY subtask URL change
    logger.debug('🔗 LazySubtaskList useEffect triggered:', {
      subtaskId,
      taskId,
      parentTaskId,
      hasLoaded,
      fullSubtasksCount: fullSubtasks.size
    });

    if (subtaskId && hasLoaded && taskId === parentTaskId) {
      logger.debug('🔗 URL taskId matches parentTaskId, loading subtask', { subtaskId, parentTaskId });

      // PERFORMANCE FIX: Check if we already have the subtask data before making API call
      const existingSubtask = fullSubtasks.get(subtaskId);
      if (existingSubtask) {
        logger.debug('🔗 Using existing subtask data for URL subtaskId:', subtaskId);
        setDetailsDialog({ open: true, subtask: existingSubtask });
        return;
      }

      // PERFORMANCE FIX: Also check subtask summaries to avoid unnecessary full load
      const summaryExists = subtaskSummaries.some(s => s.id === subtaskId);
      if (!summaryExists) {
        logger.debug('🔗 Subtask not found in summaries, skipping load for URL subtaskId:', subtaskId);
        return;
      }

      // Load the subtask directly since we know it belongs to this parent task
      setIsOpeningDialog(true);
      loadFullSubtask(subtaskId).then(subtask => {
        if (subtask) {
          logger.debug('🔗 Auto-opening SubtaskDetailsDialog for URL subtaskId:', subtaskId);
          setDetailsDialog({ open: true, subtask });
          // Clear the opening flag after a short delay to allow dialog to stabilize
          setTimeout(() => setIsOpeningDialog(false), 200);
        } else {
          logger.warn('⚠️ Subtask not found for URL subtaskId:', subtaskId);
          setIsOpeningDialog(false);
          // Navigate back to task URL if subtask not found
          handleSubtaskDialogClose();
        }
      }).catch(error => {
        logger.error('❌ Failed to load subtask for URL:', subtaskId, error);
        setIsOpeningDialog(false);
        // Navigate back to task URL on error
        handleSubtaskDialogClose();
      });
    } else if (subtaskId && hasLoaded && taskId !== parentTaskId) {
      // 🔧 IMPROVED FIX: Try to load the subtask even if URL taskId doesn't match parentTaskId
      // This handles cases where the subtask might belong to a completed task or cross-component scenarios
      logger.debug('🔍 URL taskId differs from parentTaskId, checking if subtask belongs to this component', { subtaskId, urlTaskId: taskId, parentTaskId });

      // PERFORMANCE FIX: Check if we already have the subtask data before making API call
      const existingSubtask = fullSubtasks.get(subtaskId);
      if (existingSubtask && existingSubtask.parent_task_id === parentTaskId) {
        logger.debug('✅ Using existing subtask data for cross-component check:', subtaskId);
        setDetailsDialog({ open: true, subtask: existingSubtask });
        return;
      }

      // PERFORMANCE FIX: Also check if subtask exists in summaries for this parent
      const summaryExists = subtaskSummaries.some(s => s.id === subtaskId);
      if (!summaryExists) {
        logger.debug('🚫 Subtask not found in summaries for cross-component check:', subtaskId);
        return;
      }

      // Use the direct API to check if the subtask belongs to this component's parent task
      setIsOpeningDialog(true);
      loadSubtaskById(subtaskId).then(subtask => {
        if (subtask) {
          // Subtask actually belongs to this component's parent task
          logger.debug('✅ Subtask found and belongs to this component:', subtaskId, 'opening dialog');
          setDetailsDialog({ open: true, subtask });
          // Clear the opening flag after a short delay to allow dialog to stabilize
          setTimeout(() => setIsOpeningDialog(false), 200);
        } else {
          // Subtask not found or doesn't belong to this component - this is expected
          logger.debug('🚫 Subtask not found in this component context:', subtaskId, 'this is expected for cross-component scenarios');
          setIsOpeningDialog(false);
        }
      }).catch(error => {
        logger.debug('🚫 Failed to load subtask for cross-component check', { subtaskId, error, note: 'this is expected for cross-component scenarios' });
        setIsOpeningDialog(false);
        // Silently fail for cross-component checks - this is expected behavior
      });
    } else if (!subtaskId && detailsDialog.open) {
      // Close dialog if subtaskId is removed from URL
      setDetailsDialog({ open: false, subtask: null });
    }
  }, [
    subtaskId,
    taskId,
    hasLoaded,
    loadFullSubtask,
    loadSubtaskById, // Required: used on line 441
    detailsDialog.open,
    handleSubtaskDialogClose,
    parentTaskId
    // REMOVED: fullSubtasks dependency - was causing infinite loop
    // The useEffect should only respond to URL changes, not state changes it causes
  ]);

  // Animation effect - triggers animations after state updates
  useEffect(() => {
    // Only trigger animations if we have animation triggers set
    if (animationTriggers.created.size === 0 &&
        animationTriggers.updated.size === 0 &&
        animationTriggers.deleted.size === 0) {
      return;
    }

    // Give SubtaskRow components time to register their callbacks after re-render
    const timeoutId = setTimeout(() => {
      // Trigger create animations
      animationTriggers.created.forEach(subtaskId => {
        const callbacks = rowAnimationCallbacks.current.get(subtaskId);
        if (callbacks) {
          console.log(`🎬 LazySubtaskList: Playing create animation for subtask: ${subtaskId}`);
          logger.debug('🎬 Playing create animation for subtask:', subtaskId);
          callbacks.playCreateAnimation();
        } else {
          console.log(`❌ LazySubtaskList: No callbacks found for created subtask: ${subtaskId}`);
          logger.debug('No callbacks found for created subtask:', subtaskId);
        }
      });

      // Trigger update animations
      animationTriggers.updated.forEach(subtaskId => {
        const callbacks = rowAnimationCallbacks.current.get(subtaskId);
        if (callbacks) {
          logger.debug('🎬 Playing update animation for subtask:', subtaskId);
          callbacks.playUpdateAnimation();
        } else {
          logger.debug('No callbacks found for updated subtask:', subtaskId);
        }
      });

      // Trigger delete animations
      animationTriggers.deleted.forEach(subtaskId => {
        const callbacks = rowAnimationCallbacks.current.get(subtaskId);
        if (callbacks) {
          console.log(`🎬 LazySubtaskList: Playing delete animation for subtask: ${subtaskId}`);
          logger.debug('🎬 Playing delete animation for subtask:', subtaskId);
          callbacks.playDeleteAnimation();
        } else {
          console.log(`❌ LazySubtaskList: No callbacks found for deleted subtask: ${subtaskId}`);
          logger.debug('No callbacks found for deleted subtask:', subtaskId);
        }
      });

      // Clear animation triggers after processing
      setAnimationTriggers({ created: new Set(), updated: new Set(), deleted: new Set() });
    }, 200); // Increased timeout to ensure callbacks are registered

    return () => clearTimeout(timeoutId);
  }, [animationTriggers]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

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
      logger.error('Failed to delete subtask:', error);
      // TODO: Show error toast/notification
    }
  }, []);

  // Handle subtask actions - Fixed double-click issue
  const handleSubtaskAction = useCallback((action: 'details' | 'edit' | 'complete', subtaskId: string) => {
    // Get existing subtask data if available
    const existingSubtask = fullSubtasks.get(subtaskId);

    // For details action, navigate to subtask URL instead of opening dialog directly
    if (action === 'details') {
      const subtaskUrl = `/dashboard/project/${projectId}/branch/${taskTreeId}/task/${parentTaskId}/subtask/${subtaskId}`;
      logger.debug('🔗 Navigating to subtask URL:', subtaskUrl);
      navigate(subtaskUrl);
      return; // Let URL monitoring effect handle dialog opening
    }

    // Handle other actions (edit, complete) directly
    if (existingSubtask) {
      // We have the subtask data, open dialog immediately
      switch (action) {
        case 'edit':
          setEditingSubtask(existingSubtask);
          break;
        case 'complete':
          setActiveDialog({ type: 'complete', subtaskId, subtask: existingSubtask });
          break;
      }
    } else {
      // Need to load subtask data first, then open dialog only if found
      loadFullSubtask(subtaskId).then(subtask => {
        if (subtask) {
          switch (action) {
            case 'edit':
              setEditingSubtask(subtask);
              break;
            case 'complete':
              setActiveDialog({ type: 'complete', subtaskId, subtask });
              break;
          }
        } else {
          // Subtask not found, don't open dialog and navigate away
          logger.warn('⚠️ Subtask not found, cannot open dialog:', subtaskId);
          handleSubtaskDialogClose();
        }
      }).catch(error => {
        logger.error('❌ Failed to load subtask:', subtaskId, error);
        handleSubtaskDialogClose();
      });
    }
  }, [loadFullSubtask, fullSubtasks, navigate, projectId, taskTreeId, parentTaskId]);

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
        parentTaskId={parentTaskId}
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
    parentTaskId,
    projectId,
    taskTreeId,
    handleSubtaskAction,
    handleAgentInfoClick,
    registerRowCallbacks,
    unregisterRowCallbacks
  ]);

  // Removed global loading state that caused flickering
  // Individual rows now handle their own loading states
  // Keep existing subtasks visible during refresh
  
  if (error) {
    return (
      <div className="p-4 text-center text-sm text-red-500">
        Error loading subtasks: {error}
      </div>
    );
  }
  
  // Show loading only during initial load when we have no data
  if (loading && !hasLoaded && subtaskSummaries.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        Loading subtasks...
      </div>
    );
  }

  if (subtaskSummaries.length === 0) {
    return (
      <>
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
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                logger.debug('🔘 Empty state Add Subtask button clicked');
                handleOpenCreateSubtask();
                logger.debug('📂 Create dialog state:', { createSubtaskDialogOpen: true });
              }}
            >
              <Plus className="w-3 h-3 mr-1" />
              Add Subtask
            </Button>
          </div>
        </div>

        {/* Create Subtask Dialog - Must be rendered even in empty state */}
        <SubtaskCreateDialog
          open={createSubtaskDialogOpen}
          onOpenChange={setCreateSubtaskDialogOpen}
          parentTaskId={parentTaskId}
          onClose={() => setCreateSubtaskDialogOpen(false)}
          onCreated={handleSubtaskCreated}
        />
      </>
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
        {detailsDialog.open && (
          <SubtaskDetailsDialog
            open={detailsDialog.open}
            onOpenChange={(open) => {
              if (!open && !isOpeningDialog) {
                // Only handle close events when we're not in the process of opening
                // This prevents race conditions during dialog initialization
                handleSubtaskDialogClose();
              }
            }}
            subtask={detailsDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={handleSubtaskDialogClose}
          />
        )}
      </Suspense>
      
      {/* Agent Info Dialog */}
      <Suspense fallback={null}>
        {selectedAgentForInfo && (
          <>
            {logger.debug('🚀 Rendering AgentInfoDialog:', {
              agentName: selectedAgentForInfo,
              open: agentInfoDialogOpen,
              taskTitle: `Subtask: ${subtaskSummaries.find(s => s.assignees?.includes(selectedAgentForInfo))?.title || ''}`
            })}
            <AgentInfoDialog
              open={agentInfoDialogOpen}
              onOpenChange={setAgentInfoDialogOpen}
              agentName={selectedAgentForInfo}
              taskTitle={`Subtask: ${subtaskSummaries.find(s => s.assignees?.includes(selectedAgentForInfo))?.title || ''}`}
              onClose={() => {
                logger.debug('🔒 Closing AgentInfoDialog');
                setAgentInfoDialogOpen(false);
                setSelectedAgentForInfo(null);
              }}
            />
          </>
        )}
      </Suspense>
    </div>
  );
}