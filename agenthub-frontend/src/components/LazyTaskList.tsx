import { Plus, RefreshCw } from "lucide-react";
import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState, useRef } from "react";
import { createTask, deleteTask, getAvailableAgents, listAgents, listTasks, Task } from "../api";
import { getFullTask } from "../api-lazy";
import TaskSearch from "./TaskSearch";
import TaskRow from "./TaskRow";
import { useEntityChanges } from "../hooks/useChangeSubscription";
import { ShimmerButton } from "./ui/shimmer-button";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "./ui/table";
import logger from "../utils/logger";

// Lazy-loaded components
const LazySubtaskList = lazy(() => import("./LazySubtaskList"));
const TaskDetailsDialog = lazy(() => import("./TaskDetailsDialog"));
const TaskEditDialog = lazy(() => import("./TaskEditDialog"));
const AgentAssignmentDialog = lazy(() => import("./AgentAssignmentDialog"));
const AgentInfoDialog = lazy(() => import("./AgentInfoDialog"));
const TaskContextDialog = lazy(() => import("./TaskContextDialog"));
const DeleteConfirmDialog = lazy(() => import("./DeleteConfirmDialog"));

interface LazyTaskListProps {
  projectId: string;
  taskTreeId: string;
  onTasksChanged?: () => void;
}

// Pagination configuration
const TASKS_PER_PAGE = 20;

// Lightweight task summary for initial load
interface TaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  subtask_count: number;
  assignees_count: number;
  assignees: string[];  // Add assignees array to summary
  has_dependencies: boolean;
  dependency_count: number;  // Add count of dependencies
  has_context: boolean;
}

const LazyTaskList: React.FC<LazyTaskListProps> = ({ projectId, taskTreeId, onTasksChanged }) => {
  // Core state - minimal for performance
  const [taskSummaries, setTaskSummaries] = useState<TaskSummary[]>([]);
  const [fullTasks, setFullTasks] = useState<Map<string, Task>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination state
  const [totalTasks, setTotalTasks] = useState(0);
  
  // Lazy loading state
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [loadingTasks, setLoadingTasks] = useState<Set<string>>(new Set());
  const [loadedAgents, setLoadedAgents] = useState(false);
  
  // Dialog states - simplified
  const [activeDialog, setActiveDialog] = useState<{
    type: 'details' | 'edit' | 'create' | 'assign' | 'context' | 'complete' | 'delete' | 'agent-response' | 'agent-info' | null;
    taskId?: string;
    data?: any;
  }>({ type: null });

  // Lazy data stores
  const [agents, setAgents] = useState<any[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);

  // Dependency highlighting state
  const [hoveredTaskId, setHoveredTaskId] = useState<string | null>(null);
  const [highlightedDependencies, setHighlightedDependencies] = useState<Set<string>>(new Set());

  // Track previous task IDs for detecting new tasks
  const [previousTaskIds, setPreviousTaskIds] = useState<Set<string>>(new Set());

  // Dialog saving state
  const [saving, setSaving] = useState(false);

  // Row animation callback registry
  const rowAnimationCallbacks = useRef<Map<string, {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }>>(new Map());

  // Stable refresh callback for changePoolService
  const handleTaskChanges = useCallback(async () => {
    logger.info('LazyTaskList: Task changes detected, refreshing...', { component: 'LazyTaskList' });

    // Store current task IDs and data before refresh for comparison
    const currentTaskIds = new Set(taskSummaries.map(t => t.id));
    const currentTaskMap = new Map(taskSummaries.map(t => [t.id, t]));

    // Re-fetch task summaries to get latest data
    try {
      const taskList = await listTasks({ git_branch_id: taskTreeId });
      const validTaskList = Array.isArray(taskList) ? taskList : [];

      // Convert to task summaries
      const summaries: TaskSummary[] = validTaskList.map(task => {
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
          has_context: Boolean(task.context_id || task.context_data)
        };
      });

      const newTaskIds = new Set(summaries.map(t => t.id));

      // Detect changes and trigger animations
      // 1. New tasks (created) - only if we have a previous state to compare
      if (currentTaskIds.size > 0) {
        const addedTasks = new Set([...newTaskIds].filter(id => !currentTaskIds.has(id)));
        logger.debug('Change detection statistics', {
          component: 'LazyTaskList',
          currentTaskIds: currentTaskIds.size,
          newTaskIds: newTaskIds.size,
          addedTasks: addedTasks.size
        });

        if (addedTasks.size > 0) {
          logger.info('New tasks detected', { component: 'LazyTaskList', addedTasks: [...addedTasks] });
          // Wait a bit for TaskRow to register callbacks
          setTimeout(() => {
            addedTasks.forEach(taskId => {
              const callbacks = rowAnimationCallbacks.current.get(taskId);
              if (callbacks) {
                logger.debug('Playing create animation for task', { component: 'LazyTaskList', taskId });
                callbacks.playCreateAnimation();
              } else {
                logger.warn('No callbacks found for task', { component: 'LazyTaskList', taskId });
              }
            });
          }, 100);
        }
      } else {
        logger.info('Initial load - no animation for existing tasks', { component: 'LazyTaskList' });
      }

      // 2. Removed tasks (deleted) - need to keep them in the list during animation
      const removedTasks = new Set([...currentTaskIds].filter(id => !newTaskIds.has(id)));
      if (removedTasks.size > 0) {
        logger.info('Deleted tasks detected', { component: 'LazyTaskList', removedTasks: [...removedTasks] });

        // Add deleted tasks back to the summaries temporarily for animation
        const deletedTasksData = taskSummaries.filter(task => removedTasks.has(task.id));
        summaries.push(...deletedTasksData);

        removedTasks.forEach(taskId => {
          const callbacks = rowAnimationCallbacks.current.get(taskId);
          if (callbacks) {
            logger.debug('Playing delete animation for task', { component: 'LazyTaskList', taskId });
            callbacks.playDeleteAnimation();
          } else {
            logger.warn('No callbacks found for deleted task', { component: 'LazyTaskList', taskId });
          }
        });
      }

      // 3. Updated tasks (modified)
      const updatedTasks = new Set();
      summaries.forEach(newTask => {
        const oldTask = currentTaskMap.get(newTask.id);
        if (oldTask && (
          oldTask.title !== newTask.title ||
          oldTask.status !== newTask.status ||
          oldTask.priority !== newTask.priority ||
          oldTask.subtask_count !== newTask.subtask_count ||
          oldTask.assignees.length !== newTask.assignees.length
        )) {
          updatedTasks.add(newTask.id);
        }
      });
      updatedTasks.forEach(taskId => {
        const callbacks = rowAnimationCallbacks.current.get(taskId as string);
        if (callbacks) {
          logger.debug('Playing update animation for task', { component: 'LazyTaskList', taskId });
          callbacks.playUpdateAnimation();
        }
      });

      // Update states
      setTaskSummaries(summaries);
      setTotalTasks(summaries.length);
      setPreviousTaskIds(newTaskIds);

      // Store full tasks for immediate access
      const taskMap = new Map();
      validTaskList.forEach(task => taskMap.set(task.id, task));
      setFullTasks(taskMap);

      setError(null);

    } catch (e: any) {
      logger.error('Error loading tasks in handleTaskChanges', { component: 'LazyTaskList', error: e });
      setError(e.message);
    }

    // Trigger parent component refresh if provided
    if (onTasksChanged) {
      onTasksChanged();
    }
  }, [taskSummaries, previousTaskIds, taskTreeId, onTasksChanged]);

  // Subscribe to centralized change pool for real-time updates
  // Listen to task and subtask changes for this specific branch
  useEntityChanges(
    'LazyTaskList',
    ['task', 'subtask'],
    handleTaskChanges,
    {
      branchId: taskTreeId, // Filter by specific branch
      projectId: projectId,  // Filter by specific project
      enabled: true // Always enabled - each row handles its own animation
    }
  );

  // Simple display tasks - each row handles its own animation
  const displayTasks = useMemo(() => {
    if (taskSummaries && Array.isArray(taskSummaries)) {
      return taskSummaries.slice(0, TASKS_PER_PAGE);
    }
    return [];
  }, [taskSummaries]);

  // Fallback to current implementation if lightweight endpoint isn't available
  const loadFullTasksFallback = useCallback(async () => {
    try {
      const taskList = await listTasks({ git_branch_id: taskTreeId });
      
      // Ensure taskList is a valid array
      const validTaskList = Array.isArray(taskList) ? taskList : [];
      
      // Convert to task summaries
      const summaries: TaskSummary[] = validTaskList.map(task => {
        // Check multiple possible locations for dependency data
        const depFromArray = task.dependencies?.length || 0;
        const depFromRelationships = task.dependency_relationships?.depends_on?.length || 0;
        const depFromSummary = task.dependency_summary?.total_dependencies || 0;
        
        // Use the maximum of all possible sources
        const dependencyCount = Math.max(depFromArray, depFromRelationships, depFromSummary);
        
        // Dependencies computed above
        
        return {
          id: task.id,
          title: task.title,
          status: task.status,
          priority: task.priority,
          subtask_count: task.subtasks?.length || 0,
          assignees_count: task.assignees?.length || 0,
          assignees: task.assignees || [],  // Include actual assignees array
          has_dependencies: dependencyCount > 0,
          dependency_count: dependencyCount,
          has_context: Boolean(task.context_id || task.context_data)
        };
      });
      
      setTaskSummaries(summaries);
      setTotalTasks(summaries.length);
      
      // Store full tasks for immediate access
      const taskMap = new Map();
      validTaskList.forEach(task => taskMap.set(task.id, task));
      setFullTasks(taskMap);
      
      // Clear any existing errors on successful load
      setError(null);

    } catch (e: any) {
      logger.error('Error loading tasks in loadFullTasksFallback', { component: 'LazyTaskList', error: e });
      setError(e.message);
      // Ensure we clear the loading state even on error
      throw e;
    }
  }, [taskTreeId]);

  // Initial lightweight load - only task summaries
  const loadTaskSummaries = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);
    
    try {
      // Skip the non-existent summaries endpoint and go directly to fallback
      // TODO: Implement /api/tasks/summaries endpoint for better performance
      await loadFullTasksFallback();
    } catch (error) {
      logger.error('Failed to load task summaries', { component: 'LazyTaskList', error });
      // Error is already set by loadFullTasksFallback
    } finally {
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
      // Use the proper API function that handles authentication and proper URLs
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
      logger.error('Failed to load task', { component: 'LazyTaskList', taskId, error: e });
      setLoadingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
      return null;
    }
  }, [fullTasks, loadingTasks]);

  // Load agents only when needed
  const loadAgentsOnDemand = useCallback(async () => {
    if (loadedAgents) return;
    
    try {
      const [projectAgents, availableAgentsList] = await Promise.all([
        listAgents(projectId),
        getAvailableAgents()
      ]);
      setAgents(projectAgents);
      setAvailableAgents(availableAgentsList);
      setLoadedAgents(true);
    } catch (e) {
      logger.error('Error loading agents', { component: 'LazyTaskList', error: e });
    }
  }, [projectId, loadedAgents]);

  // Load task context on demand

  // Task expansion with lazy subtask loading
  const toggleTaskExpansion = useCallback(async (taskId: string) => {
    const isExpanded = expandedTasks.has(taskId);
    
    if (isExpanded) {
      // Collapse
      setExpandedTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    } else {
      // Expand - load full task data if needed
      await loadFullTask(taskId);
      setExpandedTasks(prev => {
        const newSet = new Set(prev);
        newSet.add(taskId);
        return newSet;
      });
    }
  }, [expandedTasks, loadFullTask]);

  // Dialog handlers with lazy loading - Fixed double-click issue
  const openDialog = useCallback((type: string, taskId?: string, extraData?: any) => {
    // Set dialog state immediately to fix double-click issue
    setActiveDialog({ type: type as any, taskId, data: extraData });
    
    // Load data asynchronously after dialog is opened
    if (taskId) {
      loadFullTask(taskId);
    }
    
    if (type === 'assign') {
      loadAgentsOnDemand();
    }
  }, [loadFullTask, loadAgentsOnDemand]);

  const closeDialog = useCallback(() => {
    setActiveDialog({ type: null });
  }, []);

  // Register row animation callbacks
  const registerRowCallbacks = useCallback((taskId: string, callbacks: {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }) => {
    rowAnimationCallbacks.current.set(taskId, callbacks);
  }, []);

  // Unregister row callbacks
  const unregisterRowCallbacks = useCallback((taskId: string) => {
    rowAnimationCallbacks.current.delete(taskId);
  }, []);

  // Simple delete task handler - row animation handled independently
  const handleDeleteTask = useCallback(async (taskId: string) => {
    // Close dialog immediately for better UX
    closeDialog();

    try {
      // Call API to delete task
      await deleteTask(taskId);

      // Notify parent that task was deleted
      if (onTasksChanged) {
        onTasksChanged();
      }
    } catch (error) {
      logger.error('Failed to delete task', { component: 'LazyTaskList', error });
      // TODO: Show error message to user
    }
  }, [closeDialog, onTasksChanged]);

  // Handle creating new task
  const handleCreateTask = useCallback(async (taskData: Partial<Task>) => {
    logger.info('Creating task', { component: 'LazyTaskList', taskData, taskTreeId });

    // Check authentication
    const token = document.cookie.split('; ').find(row => row.startsWith('access_token='));
    logger.debug('Auth token status', { component: 'LazyTaskList', hasToken: !!token });
    if (token) {
      logger.debug('Token preview available', { component: 'LazyTaskList', tokenPreview: token.substring(0, 50) + '...' });
    } else {
      logger.warn('No authentication token found! You may need to log in', { component: 'LazyTaskList' });
    }

    setSaving(true);

    try {
      // Call API to create task
      const newTask = await createTask({
        ...taskData,
        git_branch_id: taskTreeId, // Ensure task is created in current branch
        assignees: taskData.assignees || [] // Use assignees from form or empty array
      });

      logger.info('Task created successfully', { component: 'LazyTaskList', newTask });

      // Close dialog after successful creation
      closeDialog();

      // Refresh the task list to show the new task
      await loadTaskSummaries(1);

      // Notify parent that task was created
      if (onTasksChanged) {
        onTasksChanged();
      }
    } catch (error: any) {
      logger.error('Failed to create task', {
        component: 'LazyTaskList',
        error,
        errorDetails: error.response || error.message || error
      });

      // Extract the actual error message
      let errorMessage = 'Unknown error';
      if (error.detail) {
        errorMessage = error.detail;
      } else if (error.message) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else {
        errorMessage = JSON.stringify(error);
      }

      alert(`Failed to create task: ${errorMessage}`);
    } finally {
      setSaving(false);
    }
  }, [closeDialog, onTasksChanged, taskTreeId, loadTaskSummaries]);

  // Initial load
  useEffect(() => {
    loadTaskSummaries(1);
  }, [projectId, taskTreeId, loadTaskSummaries]);

  // Check if we're on a small screen
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Handle task hover for dependency highlighting
  const handleTaskHover = useCallback((taskId: string | null) => {
    setHoveredTaskId(taskId);
    
    if (taskId) {
      const dependencies = new Set<string>();
      
      // Get the hovered task - prefer fullTask data, fallback to summary
      const hoveredTask = fullTasks.get(taskId);
      const hoveredSummary = taskSummaries.find(t => t.id === taskId);
      
      if (hoveredTask || hoveredSummary) {
        const task = hoveredTask || hoveredSummary;
        
        // ONLY highlight tasks that THIS task depends on (prerequisites)
        // These are the tasks that must be completed BEFORE this task can start
        
        // Add direct dependencies (tasks this task depends on)
        const taskDeps = (task as any).dependencies || [];
        taskDeps.forEach((dep: string) => {
          dependencies.add(dep);
        });
        
        // Add dependencies from dependency relationships (if any)
        const depRels = (task as any).dependency_relationships;
        if (depRels?.depends_on) {
          depRels.depends_on.forEach((dep: string) => {
            dependencies.add(dep);
          });
        }
      }
      
      setHighlightedDependencies(dependencies);
    } else {
      setHighlightedDependencies(new Set());
    }
  }, [fullTasks, taskSummaries]);

  // Render task row - unified for mobile and desktop
  const renderTaskRow = useCallback((summary: TaskSummary, isMobile: boolean) => {
    return (
      <TaskRow
        key={summary.id}
        summary={summary}
        isExpanded={expandedTasks.has(summary.id)}
        isLoading={loadingTasks.has(summary.id)}
        fullTask={fullTasks.get(summary.id) || null}
        isHighlighted={highlightedDependencies.has(summary.id)}
        isHovered={hoveredTaskId === summary.id}
        projectId={projectId}
        taskTreeId={taskTreeId}
        isMobile={isMobile}
        onPlayCreateAnimation={() => {}} // Placeholder - TaskRow will register its own callbacks
        onPlayDeleteAnimation={() => {}} // Placeholder - TaskRow will register its own callbacks
        onPlayUpdateAnimation={() => {}} // Placeholder - TaskRow will register its own callbacks
        onToggleExpansion={() => toggleTaskExpansion(summary.id)}
        onOpenDialog={openDialog}
        onHover={handleTaskHover}
        onRegisterCallbacks={registerRowCallbacks}
        onUnregisterCallbacks={unregisterRowCallbacks}
      />
    );
  }, [expandedTasks, loadingTasks, fullTasks, highlightedDependencies, hoveredTaskId, toggleTaskExpansion, openDialog, handleTaskHover, projectId, taskTreeId, registerRowCallbacks, unregisterRowCallbacks]);

  if (loading && taskSummaries.length === 0) {
    return <div className="p-4 text-center">Loading tasks...</div>;
  }
  
  if (error) {
    return <div className="p-4 text-center text-red-500">Error: {error}</div>;
  }

  return (
    <>
      {/* Custom CSS for animations */}
      <style jsx>{`
        @keyframes slideInFromRight {
          0% {
            transform: translateX(100%);
            opacity: 0;
          }
          100% {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes slideOutToRight {
          0% {
            transform: translateX(0);
            opacity: 1;
            height: auto;
          }
          70% {
            transform: translateX(100%);
            opacity: 0;
            height: auto;
          }
          100% {
            transform: translateX(100%);
            opacity: 0;
            height: 0;
            margin: 0;
            padding: 0;
            border: 0;
            overflow: hidden;
          }
        }
      `}</style>
      <div className="space-y-2">
        {/* Search Bar */}
        <div className="w-full">
          <Suspense fallback={<div>Loading search...</div>}>
            <TaskSearch
              projectId={projectId}
              taskTreeId={taskTreeId}
              onTaskSelect={(task) => openDialog('details', task.id)}
              onSubtaskSelect={(subtask, parentTask) => openDialog('details', parentTask.id)}
            />
          </Suspense>
        </div>
        
        {/* Header - Responsive */}
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 mb-2">
          <h2 className="text-lg font-semibold">
            Tasks ({totalTasks})
          </h2>
          <div className="flex gap-2">
            <ShimmerButton
              onClick={async () => {
                await loadTaskSummaries(1);
              }}
              size="sm"
              variant="outline"
              disabled={loading}
              className="flex items-center gap-1"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </ShimmerButton>
            <ShimmerButton
              onClick={() => openDialog('create')}
              size="sm"
              variant="default"
              className="flex items-center gap-1"
            >
              <Plus className="w-4 h-4" />
              New Task
            </ShimmerButton>
          </div>
        </div>
      </div>

      {/* Task List - Responsive View */}
      {isMobile ? (
        // Mobile Card View
        <div className="space-y-2">
          {displayTasks.map(task => renderTaskRow(task, true))}
        </div>
      ) : (
        // Desktop Table View
        <div className="mt-3 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                <TableHead>Title</TableHead>
                <TableHead className="hidden sm:table-cell">Status</TableHead>
                <TableHead className="hidden md:table-cell">Priority</TableHead>
                <TableHead className="hidden lg:table-cell">Dependencies</TableHead>
                <TableHead className="hidden md:table-cell">Assignees</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayTasks.map(task => renderTaskRow(task, false))}
            </TableBody>
          </Table>
        </div>
      )}


      {/* Lazy-loaded Dialogs */}
      <Suspense fallback={null}>
        {activeDialog.type === 'details' && activeDialog.taskId && (
          <TaskDetailsDialog
            open={true}
            onOpenChange={closeDialog}
            task={fullTasks.get(activeDialog.taskId) || null}
            onClose={closeDialog}
            onAgentClick={(agentName, task) => {
              closeDialog();
              openDialog('assign', task.id);
            }}
          />
        )}
        
        {activeDialog.type === 'edit' && (
          <TaskEditDialog
            open={true}
            onOpenChange={closeDialog}
            task={activeDialog.taskId ? fullTasks.get(activeDialog.taskId) || null : null}
            onClose={closeDialog}
            onSave={() => {}} // TODO: implement
            saving={false}
          />
        )}

        {activeDialog.type === 'create' && (
          <TaskEditDialog
            open={true}
            onOpenChange={closeDialog}
            task={null} // null task means create mode
            onClose={closeDialog}
            onSave={handleCreateTask}
            saving={saving}
          />
        )}

        {activeDialog.type === 'assign' && activeDialog.taskId && (
          <AgentAssignmentDialog
            open={true}
            onOpenChange={closeDialog}
            task={fullTasks.get(activeDialog.taskId) || null}
            onClose={closeDialog}
            onAssign={() => {}} // TODO: implement
            agents={agents}
            availableAgents={availableAgents}
            saving={false}
          />
        )}
        
        {activeDialog.type === 'context' && activeDialog.taskId && (
          <TaskContextDialog
            open={true}
            onOpenChange={closeDialog}
            task={fullTasks.get(activeDialog.taskId) || null}
            context={null}
            onClose={closeDialog}
            loading={false}
          />
        )}
        
        {activeDialog.type === 'delete' && activeDialog.taskId && (
          <DeleteConfirmDialog
            open={true}
            onOpenChange={closeDialog}
            onConfirm={() => handleDeleteTask(activeDialog.taskId!)}
            title="Delete Task"
            description="Are you sure you want to delete this task? This action cannot be undone."
            itemName={fullTasks.get(activeDialog.taskId)?.title || taskSummaries.find(t => t.id === activeDialog.taskId)?.title}
          />
        )}
        
        {activeDialog.type === 'agent-info' && activeDialog.data && (
          <AgentInfoDialog
            open={true}
            onOpenChange={closeDialog}
            agentName={activeDialog.data.agentName}
            taskTitle={activeDialog.data.taskTitle}
            onClose={closeDialog}
          />
        )}
      </Suspense>
    </>
  );
};

export default LazyTaskList;