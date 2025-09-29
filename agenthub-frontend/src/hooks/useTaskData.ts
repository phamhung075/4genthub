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

      // Convert to task summaries
      const summaries: TaskSummary[] = validTaskList.map(convertToTaskSummary);

      setTaskSummaries(summaries);
      setTotalTasks(summaries.length);

      // Store full tasks for immediate access
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
    const newSummary = convertToTaskSummary(taskData);

    setTaskSummaries(prev => {
      // Prevent duplicates
      if (prev.some(t => t.id === taskData.id)) {
        return prev;
      }
      return [newSummary, ...prev];
    });

    setTotalTasks(prev => prev + 1);

    setFullTasks(prev => {
      const newMap = new Map(prev);
      newMap.set(taskData.id, taskData);
      return newMap;
    });

    if (onTasksChanged) {
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