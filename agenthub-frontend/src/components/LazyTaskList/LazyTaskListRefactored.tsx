import React, { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { createTask, updateTask, deleteTask, getAvailableAgents, listAgents } from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import { useErrorToast } from "../ui/toast";
import logger from "../../utils/logger";

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
    console.log('🎯 [LazyTaskList] WebSocket notification received:', {
      entityId: notification?.entityId,
      eventType: notification?.eventType,
      hasData: !!notification?.data,
      data: notification?.data,
      metadata: notification?.metadata,
      taskTreeId,
      timestamp: new Date().toISOString()
    });

    const { entityId, eventType, data, metadata } = notification;

    // Check if this change is for our current branch
    if (metadata?.git_branch_id && metadata.git_branch_id !== taskTreeId) {
      console.log('🚫 [LazyTaskList] Ignoring notification for different branch:', {
        notificationBranch: metadata.git_branch_id,
        currentBranch: taskTreeId
      });
      return false;
    }

    if (eventType === 'api_fallback_needed') {
      console.log('🔄 [LazyTaskList] API fallback needed, reloading task summaries');
      loadTaskSummaries(1);
      return true;
    }

    if (eventType === 'created' && data) {
      console.log('✅ [LazyTaskList] Creating new task from WebSocket:', {
        taskId: data.id,
        title: data.title,
        hasAllFields: !!(data.id && data.title && data.status)
      });
      addNewTask(data);
      return true;
    } else if (eventType === 'created' && !data) {
      console.warn('⚠️ [LazyTaskList] CREATE event received but data is missing!', {
        entityId,
        metadata
      });
      // Fallback: reload all tasks
      console.log('🔄 [LazyTaskList] Falling back to full task list reload');
      loadTaskSummaries(1);
      return true;
    } else if (eventType === 'updated' && data) {
      console.log('✅ [LazyTaskList] Updating task from WebSocket:', {
        taskId: data.id,
        title: data.title
      });
      updateTaskFromData(data);
      return true;
    } else if (eventType === 'deleted') {
      console.log('✅ [LazyTaskList] Deleting task from WebSocket:', { entityId });

      // Track this deletion to prevent duplicate attempts in API callback
      wsDeletedTasksRef.current.add(entityId);
      removeTask(entityId);

      // Clear from tracking after animation completes (5 seconds)
      setTimeout(() => {
        wsDeletedTasksRef.current.delete(entityId);
      }, 5000);

      return true;
    }

    console.warn('⚠️ [LazyTaskList] Unhandled notification:', { eventType, hasData: !!data });
    return false;
  }, [taskTreeId, addNewTask, updateTaskFromData, removeTask, loadTaskSummaries]);

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

  // Display tasks
  const displayTasks = useMemo(() => {
    return taskSummaries && Array.isArray(taskSummaries)
      ? taskSummaries.slice(0, TASKS_PER_PAGE)
      : [];
  }, [taskSummaries]);

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