import React, { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getAvailableAgents, listAgents } from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import { useErrorToast, useSuccessToast } from "../ui/toast";
import logger from "../../utils/logger";

// React Query hooks
import { useQueryClient } from '@tanstack/react-query';
import { useTasks, useTaskMutations } from "../../hooks/useTasks";
import { useWebSocket } from "../../hooks/useWebSocketV2";
import { useRealtimeSync } from "../../hooks/useRealtimeSync";

// Component hooks
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
  const showSuccess = useSuccessToast();

  // State for mobile responsiveness
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // React Query data hooks
  const { data: tasks = [], isLoading: loading, refetch: loadTaskSummaries } = useTasks(taskTreeId);
  const taskMutations = useTaskMutations();
  const queryClient = useQueryClient();

  // WebSocket integration with real-time sync
  const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
  const { isConnected } = webSocketClient;
  useRealtimeSync(webSocketClient.client, true);

  // Track full task loads
  const [loadedTaskIds, setLoadedTaskIds] = useState<Set<string>>(new Set());
  const fullTasksMap = useRef<Map<string, any>>(new Map());

  // Load full task on demand
  const loadFullTask = useCallback(async (taskId: string): Promise<any | null> => {
    if (fullTasksMap.current.has(taskId)) {
      return fullTasksMap.current.get(taskId);
    }

    // Use queryClient.fetchQuery to load the full task
    try {
      const fullTask = await queryClient.fetchQuery({
        queryKey: ['task', taskId, true],
        queryFn: async () => {
          const { getTask } = await import('../../api');
          return await getTask(taskId, { includeContext: true });
        },
        staleTime: 5 * 60 * 1000
      });

      if (fullTask) {
        fullTasksMap.current.set(taskId, fullTask);
        setLoadedTaskIds(prev => new Set([...prev, taskId]));
      }
      return fullTask;
    } catch (e) {
      logger.error('Error loading full task', { taskId, error: e });
      return null;
    }
  }, [queryClient]);

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

  // Task CRUD handlers using React Query mutations
  const handleCreateTask = useCallback(async (taskData: any) => {
    if (!taskTreeId) {
      showError('Cannot create task: No branch selected.');
      return;
    }
    setSaving(true);
    try {
      await taskMutations.createTaskAsync({
        ...taskData,
        git_branch_id: taskTreeId,
        assignees: taskData.assignees || []
      });

      // Note: Success toast is handled by WebSocket (backend confirmation)
      closeDialog();
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to create task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, onTasksChanged, taskTreeId, showError, setSaving, taskMutations]);

  const handleUpdateTask = useCallback(async (taskId: string, updates: any) => {
    setSaving(true);
    try {
      await taskMutations.updateTaskAsync({
        taskId,
        updates
      });

      // Note: Success toast is handled by WebSocket (backend confirmation)
      closeDialog();
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to update task: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, onTasksChanged, showError, setSaving, taskMutations]);

  const handleDeleteTask = useCallback(async (taskId: string) => {
    closeDialog();
    try {
      await taskMutations.deleteTaskAsync(taskId);

      // Note: Success toast is handled by WebSocket (backend confirmation)
      if (onTasksChanged) onTasksChanged();
    } catch (error: any) {
      showError(`Failed to delete task: ${error.message || 'Unknown error'}`);
    }
  }, [closeDialog, onTasksChanged, showError, taskMutations]);

  // Effects
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Display tasks with pagination
  const displayTasks = useMemo(() => {
    if (!tasks || !Array.isArray(tasks)) {
      return [];
    }

    // Convert full tasks to summaries for display
    return tasks.slice(0, TASKS_PER_PAGE).map(task => ({
      id: task.id,
      title: task.title,
      status: task.status,
      priority: task.priority,
      subtask_count: task.subtask_count ?? 0,
      assignees_count: task.assignees?.length ?? 0,
      assignees: task.assignees || [],
      has_dependencies: task.dependencies?.length > 0 || task.dependency_summary?.total_dependencies > 0,
      dependency_count: task.dependencies?.length ?? task.dependency_summary?.total_dependencies ?? 0,
      has_context: Boolean(task.context_id || task.context_data),
      created_at: task.created_at
    }));
  }, [tasks]);

  // Build fullTasks map from loaded tasks
  const fullTasks = useMemo(() => {
    const map = new Map();
    loadedTaskIds.forEach(taskId => {
      const fullTask = fullTasksMap.current.get(taskId);
      if (fullTask) {
        map.set(taskId, fullTask);
      }
    });
    return map;
  }, [loadedTaskIds]);

  // Track loading state for individual tasks
  const loadingTasks = useMemo(() => {
    return new Set<string>();
  }, []);

  return (
    <>
      <TaskSearchSection
        projectId={projectId}
        taskTreeId={taskTreeId}
        onTaskSelect={(task) => openDialog('details', task.id)}
        onSubtaskSelect={(_subtask, parentTask) => openDialog('details', parentTask.id)}
      />

      <TaskListHeader
        totalTasks={tasks.length}
        isConnected={isConnected}
        loading={loading}
        onRefresh={() => loadTaskSummaries()}
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
        taskSummaries={displayTasks}
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
