import React, { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { createTask, updateTask, deleteTask, getAvailableAgents, listAgents } from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import { useErrorToast } from "../ui/toast";
import logger from "../../utils/logger";
import { taskDeletionTracker } from "../../services/taskDeletionTracker";

// Hooks
import { useTaskData } from "../../hooks/useTaskData";
import { useTaskWebSocket } from "../../hooks/useTaskWebSocket";
import { useDialogManager } from "./hooks/useDialogManager";

// Components
import { TaskListHeader, TaskListContent, TaskSearchSection, DialogSection } from "./components";

// Types
import { LazyTaskListProps, TASKS_PER_PAGE } from "../../types/taskTypes";

const LazyTaskListRefactored: React.FC<LazyTaskListProps> = ({ projectId, taskTreeId, onTasksChanged }) => {
  // Get URL parameters
  const { taskId: urlTaskId, subtaskId } = useParams<{ taskId?: string; subtaskId?: string }>();
  const navigate = useNavigate();
  const { user, tokens } = useAuth();
  const showError = useErrorToast();

  // State for mobile responsiveness
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Task data management
  const {
    taskSummaries,
    fullTasks,
    totalTasks,
    loading,
    loadingTasks,
    loadTaskSummaries,
    loadFullTask,
    updateTaskFromData,
    addNewTask,
    removeTask,
    setTotalTasks
  } = useTaskData({ taskTreeId, onTasksChanged });

  // Track WebSocket-deleted tasks to prevent duplicate delete attempts
  const wsDeletedTasksRef = useRef<Set<string>>(new Set());

  // WebSocket update handler
  const updateTaskFromWebSocket = useCallback((notification: any) => {
    logger.debug('🎯 [LazyTaskList] WebSocket notification received', {
      entityId: notification?.entityId,
      eventType: notification?.eventType,
      hasData: !!notification?.data,
      data: notification?.data,
      metadata: notification?.metadata,
      taskTreeId,
      timestamp: new Date().toISOString()
    }, 'LazyTaskListRefactored.tsx');

    const { entityId, eventType, data, metadata } = notification;

    // Branch filtering is already handled by changePoolService and useTaskWebSocket
    // No need for additional filtering here - it was causing task updates to be rejected

    if (eventType === 'api_fallback_needed') {
      logger.warn('🔄 [LazyTaskList] API fallback needed, reloading task summaries', {}, 'LazyTaskListRefactored.tsx');
      loadTaskSummaries(1);
      return true;
    }

    // FIX: Add stricter validation - check for required task fields, not just truthiness
    if (eventType === 'created' && data && data.id && data.title) {
      logger.warn('✅ [LazyTaskList] Creating new task from WebSocket - COMPLETE DATA', {
        taskId: data.id,
        title: data.title,
        hasAllFields: !!(data.id && data.title && data.status),
        willCallAddNewTask: true
      }, 'LazyTaskListRefactored.tsx');
      addNewTask(data);
      return true;
    } else if (eventType === 'created' && !data) {
      logger.warn('⚠️ [LazyTaskList] CREATE event received but data is COMPLETELY MISSING!', {
        entityId,
        metadata,
        willReloadTasks: true
      }, 'LazyTaskListRefactored.tsx');
      // Fallback: reload all tasks
      logger.warn('🔄 [LazyTaskList] Falling back to full task list reload - NO DATA', {}, 'LazyTaskListRefactored.tsx');
      loadTaskSummaries(1);
      return true;
    } else if (eventType === 'created' && data && (!data.id || !data.title)) {
      // NEW: Handle case where data exists but is incomplete (empty object {})
      logger.warn('⚠️ [LazyTaskList] CREATE event has INCOMPLETE task data (missing id or title)', {
        entityId,
        hasData: !!data,
        hasId: !!data.id,
        hasTitle: !!data.title,
        dataKeys: Object.keys(data),
        metadata,
        willReloadTasks: true
      }, 'LazyTaskListRefactored.tsx');
      // Fallback: reload all tasks
      logger.warn('🔄 [LazyTaskList] Falling back to full task list reload - INCOMPLETE DATA', {}, 'LazyTaskListRefactored.tsx');
      loadTaskSummaries(1);
      return true;
    } else if (eventType === 'updated' && data && data.id) {
      logger.debug('✅ [LazyTaskList] Updating task from WebSocket', {
        component: 'LazyTaskList',
        taskId: data.id,
        title: data.title
      }, 'LazyTaskListRefactored.tsx');
      updateTaskFromData(data);
      return true;
    } else if (eventType === 'completed' && data && data.id) {
      // Completed is semantically an update (task status changed to done)
      logger.debug('✅ [LazyTaskList] Task completed from WebSocket', {
        component: 'LazyTaskList',
        taskId: data.id,
        title: data.title,
        status: data.status
      }, 'LazyTaskListRefactored.tsx');
      updateTaskFromData(data);
      return true;
    } else if (eventType === 'deleted') {
      logger.debug('✅ [LazyTaskList] Deleting task from WebSocket', {
        component: 'LazyTaskList',
        entityId
      }, 'LazyTaskListRefactored.tsx');

      // Track this deletion to prevent duplicate attempts in API callback
      wsDeletedTasksRef.current.add(entityId);

      // Mark for deletion so TaskRow can detect and animate
      taskDeletionTracker.markForDeletion(entityId);

      // Remove from state after animation completes (800ms animation + 200ms buffer)
      setTimeout(() => {
        logger.debug('🗑️ [LazyTaskList] Removing task after animation', { entityId }, 'LazyTaskListRefactored.tsx');

        // BUGFIX: Only remove if task still exists in state (hasn't been removed by API callback)
        // This prevents double-decrement of totalTasks count
        if (taskSummaries.some(t => t.id === entityId)) {
          removeTask(entityId);
        } else {
          logger.debug('⚠️ [LazyTaskList] Task already removed by API, skipping WebSocket removal', { entityId }, 'LazyTaskListRefactored.tsx');
        }

        wsDeletedTasksRef.current.delete(entityId);
        taskDeletionTracker.clearDeletion(entityId);
      }, 1000);

      return true;
    }

    logger.warn('⚠️ [LazyTaskList] Unhandled notification:', { eventType, hasData: !!data });
    return false;
  }, [taskTreeId, addNewTask, updateTaskFromData, removeTask, loadTaskSummaries, taskSummaries]);

  // WebSocket integration
  const { isConnected, branchTaskTotal } = useTaskWebSocket({
    userId: user?.id || '',
    token: tokens?.access_token || '',
    taskTreeId,
    projectId,
    onTaskUpdate: updateTaskFromWebSocket
  });

  // UI state
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [loadedAgents, setLoadedAgents] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);
  const [hoveredTaskId, setHoveredTaskId] = useState<string | null>(null);
  const [highlightedDependencies, setHighlightedDependencies] = useState<Set<string>>(new Set());

  // Load agents on demand
  const loadAgentsOnDemand = useCallback(async () => {
    if (loadedAgents) return;
    try {
      const [projectAgents, availableAgentsList] = await Promise.all([
        listAgents(),
        getAvailableAgents()
      ]);
      setAgents(projectAgents);
      setAvailableAgents(availableAgentsList);
      setLoadedAgents(true);
    } catch (e) {
      logger.error('Error loading agents', { component: 'LazyTaskList', error: e });
    }
  }, [loadedAgents]);

  // Dialog management
  const { activeDialog, openDialog, closeDialog, saving, setSaving, isClosingRef } = useDialogManager(
    projectId,
    taskTreeId,
    urlTaskId,
    subtaskId,
    loadFullTask,
    loadAgentsOnDemand
  );

  // Track the last processed taskId to prevent reopening loops
  const lastProcessedTaskIdRef = useRef<string | undefined>(undefined);

  // Auto-open task dialog from URL
  useEffect(() => {
    const autoOpenTask = async () => {
      // Skip if we're in the middle of closing
      if (isClosingRef.current) {
        return;
      }

      // Only process if taskId actually changed
      if (urlTaskId !== lastProcessedTaskIdRef.current) {
        lastProcessedTaskIdRef.current = urlTaskId;

        if (urlTaskId && activeDialog.type === null) {
          // Load the task and open dialog
          openDialog('details', urlTaskId);
        } else if (!urlTaskId && activeDialog.type === 'details') {
          // URL changed (back button) - close dialog
          closeDialog();
        }
      }
    };

    autoOpenTask();
  }, [urlTaskId, activeDialog.type, openDialog, closeDialog, isClosingRef]);

  // Task expansion
  const toggleTaskExpansion = useCallback(async (taskId: string) => {
    const isExpanded = expandedTasks.has(taskId);
    if (isExpanded) {
      setExpandedTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    } else {
      await loadFullTask(taskId);
      setExpandedTasks(prev => {
        const newSet = new Set(prev);
        newSet.add(taskId);
        return newSet;
      });
    }
  }, [expandedTasks, loadFullTask]);

  // Task CRUD handlers
  const handleCreateTask = useCallback(async (taskData: any) => {
    if (!taskTreeId) {
      showError('Cannot create task: No branch selected.');
      return;
    }
    setSaving(true);
    try {
      const newTask = await createTask({
        ...taskData,
        git_branch_id: taskTreeId,
        assignees: taskData.assignees || []
      });
      // WebSocket will handle the update via addNewTask, no need for manual refresh
      closeDialog();
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to create task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, onTasksChanged, taskTreeId, showError, setSaving]);

  const handleUpdateTask = useCallback(async (taskId: string, updates: any) => {
    setSaving(true);
    try {
      const updatedTask = await updateTask(taskId, updates);
      // WebSocket will handle the update via updateTaskFromData, no need for manual refresh
      closeDialog();
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to update task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, onTasksChanged, showError, setSaving]);

  const handleDeleteTask = useCallback(async (taskId: string) => {
    closeDialog();
    try {
      await deleteTask(taskId);

      // Only update UI if WebSocket hasn't already handled it
      // This prevents duplicate delete attempts and 404 errors
      if (!wsDeletedTasksRef.current.has(taskId)) {
        removeTask(taskId);
      }

      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      // Only show error if WebSocket didn't already delete it
      // WebSocket deletion means the task was successfully removed
      if (!wsDeletedTasksRef.current.has(taskId)) {
        showError(`Failed to delete task: ${error.message || 'Unknown error'}`);
      }
    }
  }, [closeDialog, onTasksChanged, showError, removeTask]);

  // Effects
  // Load initial tasks when taskTreeId changes
  useEffect(() => {
    if (taskTreeId) {
      loadTaskSummaries(1);
    }
  }, [taskTreeId, loadTaskSummaries]);

  useEffect(() => {
    if (typeof branchTaskTotal === "number" && !Number.isNaN(branchTaskTotal) && branchTaskTotal > 0) {
      setTotalTasks(prevTotal => prevTotal !== branchTaskTotal ? branchTaskTotal : prevTotal);
    }
  }, [branchTaskTotal, setTotalTasks]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Display tasks - DON'T filter out deleting tasks (let animation play first)
  const displayTasks = useMemo(() => {
    if (!taskSummaries || !Array.isArray(taskSummaries)) {
      return [];
    }

    // Keep all tasks including those being deleted
    // The delete animation will play, then the task will be removed after timeout
    return taskSummaries.slice(0, TASKS_PER_PAGE);
  }, [taskSummaries, totalTasks]); // Include totalTasks to force re-computation when new tasks are added

  return (
    <>
      <TaskSearchSection
        projectId={projectId}
        taskTreeId={taskTreeId}
        onTaskSelect={(task) => openDialog('details', task.id)}
        onSubtaskSelect={(_subtask, parentTask) => openDialog('details', parentTask.id)}
      />

      <TaskListHeader
        totalTasks={totalTasks}
        isConnected={isConnected}
        loading={loading}
        onRefresh={() => loadTaskSummaries(1)}
        onCreateNew={() => openDialog('create')}
      />

      <TaskListContent
        displayTasks={displayTasks}
        isMobile={isMobile}
        expandedTasks={expandedTasks}
        loadingTasks={loadingTasks}
        fullTasks={fullTasks}
        highlightedDependencies={highlightedDependencies}
        hoveredTaskId={hoveredTaskId}
        projectId={projectId}
        taskTreeId={taskTreeId}
        onToggleExpand={toggleTaskExpansion}
        onOpenDialog={openDialog}
        onHoverTask={setHoveredTaskId}
        onHighlightDependencies={setHighlightedDependencies}
      />

      <DialogSection
        activeDialog={activeDialog}
        fullTasks={fullTasks}
        taskSummaries={taskSummaries}
        agents={agents}
        availableAgents={availableAgents}
        saving={saving}
        onCloseDialog={closeDialog}
        onOpenDialog={openDialog}
        onUpdateTask={handleUpdateTask}
        onCreateTask={handleCreateTask}
        onDeleteTask={handleDeleteTask}
      />
    </>
  );
};

export default LazyTaskListRefactored;