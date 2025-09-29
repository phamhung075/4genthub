import React, { useCallback, useEffect, useMemo, useState } from "react";
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

  // WebSocket update handler
  const updateTaskFromWebSocket = useCallback((notification: any) => {
    const { entityId, eventType, data, metadata } = notification;

    // Check if this change is for our current branch
    if (metadata?.git_branch_id && metadata.git_branch_id !== taskTreeId) {
      return false;
    }

    if (eventType === 'api_fallback_needed') {
      loadTaskSummaries(1);
      return true;
    }

    if (eventType === 'created' && data) {
      addNewTask(data);
      return true;
    } else if (eventType === 'updated' && data) {
      updateTaskFromData(data);
      return true;
    } else if (eventType === 'deleted') {
      removeTask(entityId);
      return true;
    }

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
  const navigateBack = useCallback(() => {
    navigate(`/dashboard/project/${projectId}/branch/${taskTreeId}`);
  }, [navigate, projectId, taskTreeId]);

  const { activeDialog, openDialog, closeDialog, saving, setSaving } = useDialogManager(
    urlTaskId,
    subtaskId,
    navigateBack,
    loadFullTask,
    loadAgentsOnDemand
  );

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
      addNewTask(newTask);
      closeDialog();
      await loadTaskSummaries(1);
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to create task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, addNewTask, loadTaskSummaries, onTasksChanged, taskTreeId, showError, setSaving]);

  const handleUpdateTask = useCallback(async (taskId: string, updates: any) => {
    setSaving(true);
    try {
      const updatedTask = await updateTask(taskId, updates);
      updateTaskFromData(updatedTask);
      closeDialog();
      await loadTaskSummaries(1);
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to update task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, updateTaskFromData, loadTaskSummaries, onTasksChanged, showError, setSaving]);

  const handleDeleteTask = useCallback(async (taskId: string) => {
    closeDialog();
    try {
      await deleteTask(taskId);
      removeTask(taskId);
      await loadTaskSummaries(1);
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to delete task: ${error.message || 'Unknown error'}`);
    }
  }, [closeDialog, removeTask, loadTaskSummaries, onTasksChanged, showError]);

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