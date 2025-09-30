import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { Task } from '../api';
import { listTasks } from '../api';
import { getFullTask } from '../api-lazy';
import logger from '../utils/logger';
import { TaskSummary } from '../types/taskTypes';

interface UseTaskDataOptions {
  taskTreeId: string;
  onTasksChanged?: () => void;
}

interface UseTaskDataReturn {
  // State
  taskSummaries: TaskSummary[];
  fullTasks: Map<string, Task>;
  totalTasks: number;
  loading: boolean;
  error: string | null;
  loadingTasks: Set<string>;

  // Actions
  loadTaskSummaries: (page?: number) => Promise<void>;
  loadFullTask: (taskId: string) => Promise<Task | null>;
  updateTaskFromData: (taskData: Task) => void;
  addNewTask: (taskData: Task) => void;
  removeTask: (taskId: string) => void;
  setTotalTasks: React.Dispatch<React.SetStateAction<number>>;

  // Utilities
  convertToTaskSummary: (task: any) => TaskSummary;
}

export function useTaskData({ taskTreeId, onTasksChanged }: UseTaskDataOptions): UseTaskDataReturn {
  // Reset state when taskTreeId changes
  const prevTaskTreeId = useRef<string>();

  // Core state
  const [taskSummaries, setTaskSummaries] = useState<TaskSummary[]>([]);
  const [fullTasks, setFullTasks] = useState<Map<string, Task>>(new Map());
  const [totalTasks, setTotalTasks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingTasks, setLoadingTasks] = useState<Set<string>>(new Set());

  // Loading state ref to prevent infinite loops
  const isLoadingRef = useRef(false);

  // Reset state when taskTreeId changes
  useEffect(() => {
    if (prevTaskTreeId.current && prevTaskTreeId.current !== taskTreeId) {
      setTaskSummaries([]);
      setFullTasks(new Map());
      setTotalTasks(0);
      setError(null);
      setLoadingTasks(new Set());
    }
    prevTaskTreeId.current = taskTreeId;
  }, [taskTreeId]);

  // Helper function to convert full task to task summary
  const convertToTaskSummary = useCallback((task: any): TaskSummary => {
    const depFromArray = task.dependencies?.length || 0;
    const depFromRelationships = task.dependency_relationships?.depends_on?.length || 0;
    const depFromSummary = task.dependency_summary?.total_dependencies || 0;
    const dependencyCount = Math.max(depFromArray, depFromRelationships, depFromSummary);

    return {
      id: task.id,
      title: task.title,
      status: task.status,
      priority: task.priority,
      subtask_count: task.subtasks?.length || 0,
      assignees_count: task.assignees?.length || 0,
      assignees: task.assignees || [],
      has_dependencies: dependencyCount > 0,
      dependency_count: dependencyCount,
      has_context: Boolean(task.context_id || task.context_data),
      created_at: task.created_at
    };
  }, []);

  // Fallback API call to load full tasks
  const loadFullTasksFallback = useCallback(async () => {
    try {
      const taskList = await listTasks({ git_branch_id: taskTreeId });

      // Ensure taskList is a valid array
      const validTaskList = Array.isArray(taskList) ? taskList : [];

      // CRITICAL FIX: Filter out subtasks (tasks with parent_task_id)
      // Subtasks should only appear nested under their parent, not as top-level tasks
      const topLevelTasks = validTaskList.filter(task => !task.parent_task_id);

      // Convert to task summaries (only top-level tasks)
      const summaries: TaskSummary[] = topLevelTasks.map(convertToTaskSummary);

      setTaskSummaries(summaries);
      setTotalTasks(summaries.length);

      // Store full tasks for immediate access (including subtasks for expansion)
      const taskMap = new Map();
      validTaskList.forEach(task => taskMap.set(task.id, task));
      setFullTasks(taskMap);

      // Clear any existing errors on successful load
      setError(null);

    } catch (e: any) {
      logger.error('Error loading tasks in loadFullTasksFallback', {
        component: 'useTaskData',
        error: e
      });
      setError(e.message);
      throw e;
    }
  }, [taskTreeId, convertToTaskSummary]);

  // Load task summaries (initial load)
  const loadTaskSummaries = useCallback(async (page = 1) => {
    // Prevent duplicate calls while loading
    if (isLoadingRef.current) {
      logger.debug('Already loading tasks, skipping duplicate call', {
        component: 'useTaskData'
      });
      return;
    }

    logger.info('Loading task summaries', {
      component: 'useTaskData',
      page
    });

    isLoadingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      // Use fallback method for now - TODO: implement lightweight endpoint
      await loadFullTasksFallback();
    } catch (error) {
      logger.error('Failed to load task summaries', {
        component: 'useTaskData',
        error
      });
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
    }
  }, [loadFullTasksFallback]);

  // Load full task data on demand
  const loadFullTask = useCallback(async (taskId: string): Promise<Task | null> => {
    if (fullTasks.has(taskId)) {
      return fullTasks.get(taskId) || null;
    }

    if (loadingTasks.has(taskId)) {
      return null; // Already loading
    }

    setLoadingTasks(prev => {
      const newSet = new Set(prev);
      newSet.add(taskId);
      return newSet;
    });

    try {
      const task = await getFullTask(taskId);

      if (task) {
        setFullTasks(prev => {
          const newMap = new Map(prev);
          newMap.set(taskId, task);
          return newMap;
        });
      }

      setLoadingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });

      return task;

    } catch (e) {
      logger.error('Failed to load task', {
        component: 'useTaskData',
        taskId,
        error: e
      });

      setLoadingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });

      return null;
    }
  }, [fullTasks, loadingTasks]);

  // Update task from external data (e.g., WebSocket)
  const updateTaskFromData = useCallback((taskData: Task) => {
    // CRITICAL FIX: Don't update summaries for subtasks
    // Subtasks should only be stored in fullTasks map
    if (taskData.parent_task_id) {
      // This is a subtask - only update in fullTasks map
      setFullTasks(prev => {
        const newMap = new Map(prev);
        newMap.set(taskData.id, taskData);
        return newMap;
      });

      if (onTasksChanged) {
        onTasksChanged();
      }
      return;
    }

    // This is a top-level task - update summaries
    const updatedSummary = convertToTaskSummary(taskData);

    setTaskSummaries(prev => prev.map(task =>
      task.id === taskData.id ? updatedSummary : task
    ));

    setFullTasks(prev => {
      const newMap = new Map(prev);
      newMap.set(taskData.id, taskData);
      return newMap;
    });

    if (onTasksChanged) {
      onTasksChanged();
    }
  }, [convertToTaskSummary, onTasksChanged]);

  // Add new task
  const addNewTask = useCallback((taskData: Task) => {
    console.log('🔍 [useTaskData] addNewTask called with:', {
      hasData: !!taskData,
      taskId: taskData?.id,
      taskTitle: taskData?.title,
      isSubtask: !!taskData?.parent_task_id,
      dataKeys: taskData ? Object.keys(taskData) : [],
      fullData: taskData
    });

    // CRITICAL FIX: Don't add subtasks to main task list
    // Subtasks should only appear nested under their parent task
    if (taskData.parent_task_id) {
      console.log('✅ [useTaskData] Adding subtask to fullTasks map:', {
        subtaskId: taskData.id,
        parentTaskId: taskData.parent_task_id
      });

      // This is a subtask - only store in fullTasks map, don't add to summaries
      setFullTasks(prev => {
        const newMap = new Map(prev);
        newMap.set(taskData.id, taskData);
        console.log('✅ [useTaskData] Subtask added, fullTasks size:', newMap.size);
        return newMap;
      });

      if (onTasksChanged) {
        onTasksChanged();
      }
      return;
    }

    console.log('✅ [useTaskData] Adding top-level task to summaries:', {
      taskId: taskData.id,
      taskTitle: taskData.title
    });

    // This is a top-level task - add to summaries
    const newSummary = convertToTaskSummary(taskData);
    console.log('✅ [useTaskData] Converted to summary:', newSummary);

    setTaskSummaries(prev => {
      // Prevent duplicates
      if (prev.some(t => t.id === taskData.id)) {
        console.log('⚠️ [useTaskData] Task already exists in summaries, skipping duplicate');
        return prev;
      }
      console.log('✅ [useTaskData] Adding task to summaries, previous count:', prev.length);
      const newSummaries = [newSummary, ...prev];
      console.log('✅ [useTaskData] New summaries count:', newSummaries.length);
      return newSummaries;
    });

    setTotalTasks(prev => {
      const newTotal = prev + 1;
      console.log('✅ [useTaskData] Updated totalTasks:', prev, '->', newTotal);
      return newTotal;
    });

    setFullTasks(prev => {
      const newMap = new Map(prev);
      newMap.set(taskData.id, taskData);
      console.log('✅ [useTaskData] Added task to fullTasks, size:', newMap.size);
      return newMap;
    });

    if (onTasksChanged) {
      console.log('✅ [useTaskData] Calling onTasksChanged callback');
      onTasksChanged();
    }
  }, [convertToTaskSummary, onTasksChanged]);

  // Remove task
  const removeTask = useCallback((taskId: string) => {
    setTaskSummaries(prev => prev.filter(task => task.id !== taskId));
    setTotalTasks(prev => Math.max(0, prev - 1));

    setFullTasks(prev => {
      const newMap = new Map(prev);
      newMap.delete(taskId);
      return newMap;
    });

    if (onTasksChanged) {
      onTasksChanged();
    }
  }, [onTasksChanged]);

  return {
    // State
    taskSummaries,
    fullTasks,
    totalTasks,
    loading,
    error,
    loadingTasks,

    // Actions
    loadTaskSummaries,
    loadFullTask,
    updateTaskFromData,
    addNewTask,
    removeTask,
    setTotalTasks,

    // Utilities
    convertToTaskSummary,
  };
}