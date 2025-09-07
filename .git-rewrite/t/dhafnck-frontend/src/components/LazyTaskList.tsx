import { Eye, FileText, Pencil, Plus, Trash2, Users, ChevronDown, ChevronRight } from "lucide-react";
import React, { useEffect, useState, useCallback, useMemo, lazy, Suspense } from "react";
import { listTasks, Task, listAgents, getAvailableAgents, deleteTask } from "../api";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { RefreshButton } from "./ui/refresh-button";
import TaskSearch from "./TaskSearch";

// Lazy-loaded components
const LazySubtaskList = lazy(() => import("./LazySubtaskList"));
const TaskDetailsDialog = lazy(() => import("./TaskDetailsDialog"));
const TaskEditDialog = lazy(() => import("./TaskEditDialog"));
const AgentAssignmentDialog = lazy(() => import("./AgentAssignmentDialog"));
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
  has_dependencies: boolean;
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
    type: 'details' | 'edit' | 'create' | 'assign' | 'context' | 'complete' | 'delete' | 'agent-response' | null;
    taskId?: string;
    data?: any;
  }>({ type: null });

  // Lazy data stores
  const [agents, setAgents] = useState<any[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);

  // Memoized filtered and sorted tasks
  const displayTasks = useMemo(() => {
    // Defensive check to prevent crashes
    if (!taskSummaries || !Array.isArray(taskSummaries)) {
      return [];
    }
    return taskSummaries.slice(0, TASKS_PER_PAGE);
  }, [taskSummaries]);

  // Fallback to current implementation if lightweight endpoint isn't available
  const loadFullTasksFallback = useCallback(async () => {
    try {
      console.log('Loading tasks for branch:', taskTreeId);
      const taskList = await listTasks({ git_branch_id: taskTreeId });
      
      // Log the response to debug
      console.log('Task list response:', taskList);
      
      // Ensure taskList is a valid array
      const validTaskList = Array.isArray(taskList) ? taskList : [];
      
      // Convert to task summaries
      const summaries: TaskSummary[] = validTaskList.map(task => ({
        id: task.id,
        title: task.title,
        status: task.status,
        priority: task.priority,
        subtask_count: task.subtasks?.length || 0,
        assignees_count: task.assignees?.length || 0,
        has_dependencies: Boolean(task.dependencies?.length),
        has_context: Boolean(task.context_id || task.context_data)
      }));
      
      console.log('Converted summaries:', summaries);
      
      setTaskSummaries(summaries);
      setTotalTasks(summaries.length);
      
      // Store full tasks for immediate access
      const taskMap = new Map();
      validTaskList.forEach(task => taskMap.set(task.id, task));
      setFullTasks(taskMap);
      
    } catch (e: any) {
      console.error('Error loading tasks:', e);
      setError(e.message);
    }
  }, [taskTreeId]);

  // Initial lightweight load - only task summaries
  const loadTaskSummaries = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);
    
    // Skip the non-existent summaries endpoint and go directly to fallback
    // TODO: Implement /api/tasks/summaries endpoint for better performance
    await loadFullTasksFallback();
    setLoading(false);
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
      // Request single task with full data
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const task = await response.json();
      
      setFullTasks(prev => {
        const newMap = new Map(prev);
        newMap.set(taskId, task);
        return newMap;
      });
      setLoadingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
      
      return task;
      
    } catch (e) {
      console.error(`Failed to load task ${taskId}:`, e);
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
      console.error('Error loading agents:', e);
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

  // Dialog handlers with lazy loading
  const openDialog = useCallback(async (type: string, taskId?: string, extraData?: any) => {
    if (taskId) {
      await loadFullTask(taskId);
    }
    
    if (type === 'assign') {
      await loadAgentsOnDemand();
    }
    
    setActiveDialog({ type: type as any, taskId, data: extraData });
  }, [loadFullTask, loadAgentsOnDemand]);

  const closeDialog = useCallback(() => {
    setActiveDialog({ type: null });
  }, []);

  // Delete task handler
  const handleDeleteTask = useCallback(async (taskId: string) => {
    try {
      const success = await deleteTask(taskId);
      if (success) {
        // Remove from summaries
        setTaskSummaries(prev => prev.filter(t => t.id !== taskId));
        // Remove from full tasks
        setFullTasks(prev => {
          const newMap = new Map(prev);
          newMap.delete(taskId);
          return newMap;
        });
        // Update total count
        setTotalTasks(prev => Math.max(0, prev - 1));
        // Notify parent
        if (onTasksChanged) {
          onTasksChanged();
        }
      }
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
    closeDialog();
  }, [onTasksChanged, closeDialog]);

  // Load more tasks (pagination) - simplified version
  const loadMoreTasks = useCallback(async () => {
    if (loading) return;
    
    const nextPage = Math.floor(taskSummaries.length / TASKS_PER_PAGE) + 1;
    await loadTaskSummaries(nextPage);
  }, [loading, taskSummaries.length, loadTaskSummaries]);

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

  // Render task row for mobile (card view)
  const renderMobileTaskCard = useCallback((summary: TaskSummary) => {
    const isExpanded = expandedTasks.has(summary.id);
    const isLoading = loadingTasks.has(summary.id);
    const fullTask = fullTasks.get(summary.id) || null;
    
    return (
      <div key={summary.id} className="bg-surface dark:bg-gray-800 rounded-lg shadow-sm border border-surface-border dark:border-gray-700 mb-3">
        <div className="p-4">
          {/* Task Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <h3 className="font-medium text-base mb-2 pr-2">{summary.title}</h3>
              <div className="flex flex-wrap gap-2">
                <Badge className="text-xs">{summary.status}</Badge>
                <Badge variant="secondary" className="text-xs">{summary.priority}</Badge>
                {summary.subtask_count > 0 && (
                  <Badge variant="outline" className="text-xs">
                    {summary.subtask_count} subtasks
                  </Badge>
                )}
                {summary.has_dependencies && (
                  <Badge variant="outline" className="text-xs">
                    Has deps
                  </Badge>
                )}
                {summary.assignees_count > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {summary.assignees_count} assigned
                  </Badge>
                )}
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8"
              onClick={() => toggleTaskExpansion(summary.id)}
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              ) : isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </Button>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-1 flex-wrap">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => openDialog('details', summary.id)}
              className="flex-1 min-w-[60px]"
            >
              <Eye className="w-3 h-3 mr-1" />
              View
            </Button>
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => openDialog('edit', summary.id)}
              className="flex-1 min-w-[60px]"
            >
              <Pencil className="w-3 h-3 mr-1" />
              Edit
            </Button>
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => openDialog('assign', summary.id)}
              className="flex-1 min-w-[60px]"
            >
              <Users className="w-3 h-3 mr-1" />
              Assign
            </Button>
            
            {summary.has_context && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => openDialog('context', summary.id)}
                title="View context"
              >
                <FileText className="w-3 h-3" />
              </Button>
            )}
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => openDialog('delete', summary.id)}
              title="Delete task"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        </div>

        {/* Expanded Content */}
        {isExpanded && fullTask && (
          <div className="border-t border-surface-border dark:border-gray-700">
            <div className="border-l-4 border-blue-400 dark:border-blue-600">
              <Suspense fallback={<div className="p-4 text-center text-sm text-muted-foreground">Loading subtasks...</div>}>
                <LazySubtaskList 
                  projectId={projectId} 
                  taskTreeId={taskTreeId} 
                  parentTaskId={summary.id}
                />
              </Suspense>
            </div>
          </div>
        )}
      </div>
    );
  }, [expandedTasks, loadingTasks, fullTasks, toggleTaskExpansion, openDialog, projectId, taskTreeId]);

  // Render task row for desktop (table view)
  const renderDesktopTaskRow = useCallback((summary: TaskSummary) => {
    const isExpanded = expandedTasks.has(summary.id);
    const isLoading = loadingTasks.has(summary.id);
    const fullTask = fullTasks.get(summary.id) || null;
    
    return (
      <React.Fragment key={summary.id}>
        <TableRow>
          <TableCell className="w-[50px]">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => toggleTaskExpansion(summary.id)}
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              ) : isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </Button>
          </TableCell>
          
          <TableCell>
            <div className="flex items-center gap-2">
              <span>{summary.title}</span>
              {summary.subtask_count > 0 && (
                <Badge variant="outline" className="text-xs">
                  {summary.subtask_count}
                </Badge>
              )}
            </div>
          </TableCell>
          
          <TableCell className="hidden sm:table-cell">
            <Badge>{summary.status}</Badge>
          </TableCell>
          
          <TableCell className="hidden md:table-cell">
            <Badge variant="secondary">{summary.priority}</Badge>
          </TableCell>
          
          <TableCell className="hidden lg:table-cell">
            {summary.has_dependencies ? (
              <Badge variant="outline" className="text-xs">
                Has dependencies
              </Badge>
            ) : (
              <span className="text-xs text-muted-foreground">None</span>
            )}
          </TableCell>
          
          <TableCell className="hidden xl:table-cell">
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
                size="icon"
                onClick={() => openDialog('details', summary.id)}
                title="View details"
                className="h-8 w-8"
              >
                <Eye className="w-4 h-4" />
              </Button>
              
              {summary.has_context && (
                <Button 
                  variant="ghost" 
                  size="icon"
                  onClick={() => openDialog('context', summary.id)}
                  title="View context"
                  className="h-8 w-8 hidden sm:inline-flex"
                >
                  <FileText className="w-4 h-4" />
                </Button>
              )}
              
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => openDialog('assign', summary.id)}
                title="Assign agents"
                className="h-8 w-8 hidden sm:inline-flex"
              >
                <Users className="w-4 h-4" />
              </Button>
              
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => openDialog('edit', summary.id)}
                title="Edit task"
                className="h-8 w-8"
              >
                <Pencil className="w-4 h-4" />
              </Button>
              
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => openDialog('delete', summary.id)}
                title="Delete task"
                className="h-8 w-8"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
        
        {isExpanded && fullTask && (
          <TableRow className="bg-background-secondary dark:bg-gray-900/50">
            <TableCell colSpan={7} className="p-0">
              <div className="border-l-4 border-blue-400 dark:border-blue-600 ml-8">
                <Suspense fallback={<div className="p-4 text-center text-sm text-muted-foreground">Loading subtasks...</div>}>
                  <LazySubtaskList 
                    projectId={projectId} 
                    taskTreeId={taskTreeId} 
                    parentTaskId={summary.id}
                  />
                </Suspense>
              </div>
            </TableCell>
          </TableRow>
        )}
      </React.Fragment>
    );
  }, [expandedTasks, loadingTasks, fullTasks, toggleTaskExpansion, openDialog, projectId, taskTreeId]);

  if (loading && taskSummaries.length === 0) {
    return <div className="p-4 text-center">Loading tasks...</div>;
  }
  
  if (error) {
    return <div className="p-4 text-center text-red-500">Error: {error}</div>;
  }

  return (
    <>
      <div className="space-y-4">
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
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
          <h2 className="text-lg font-semibold">
            Tasks ({totalTasks})
          </h2>
          <div className="flex gap-2">
            <Button
              onClick={() => openDialog('create')}
              size={isMobile ? "default" : "sm"}
              variant="default"
              className="flex items-center gap-1 flex-1 sm:flex-initial"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">New Task</span>
              <span className="sm:hidden">New</span>
            </Button>
            <RefreshButton 
              onClick={() => loadTaskSummaries(1)} 
              loading={loading}
              size={isMobile ? "default" : "sm"}
            />
          </div>
        </div>
      </div>

      {/* Task List - Responsive View */}
      {isMobile ? (
        // Mobile Card View
        <div className="space-y-3">
          {displayTasks.map(renderMobileTaskCard)}
        </div>
      ) : (
        // Desktop Table View
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                <TableHead>Title</TableHead>
                <TableHead className="hidden sm:table-cell">Status</TableHead>
                <TableHead className="hidden md:table-cell">Priority</TableHead>
                <TableHead className="hidden lg:table-cell">Dependencies</TableHead>
                <TableHead className="hidden xl:table-cell">Assignees</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayTasks.map(renderDesktopTaskRow)}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Load More Button */}
      {taskSummaries.length > 0 && (
        <div className="flex justify-center p-4">
          <Button
            onClick={loadMoreTasks}
            disabled={loading}
            variant="outline"
          >
            {loading ? 'Loading...' : 'Load More Tasks'}
          </Button>
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
            onAgentClick={() => {}} // TODO: implement
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
      </Suspense>
    </>
  );
};

export default LazyTaskList;