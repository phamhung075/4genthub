import { Check, Eye, FileText, Link, Minus, Pencil, Plus, Trash2, Users } from "lucide-react";
import React, { useEffect, useState } from "react";
import { listTasks, Task, Subtask, updateTask, getTaskContext, listAgents, getAvailableAgents, callAgent, createTask, completeTask, deleteTask } from "../api";
import { SubtaskList } from "./SubtaskList";
import { ShimmerBadge } from "./ui/shimmer-badge";
import { ShimmerButton } from "./ui/shimmer-button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { RefreshButton } from "./ui/refresh-button";
import TaskSearch from "./TaskSearch";

// Import all the new modular components
import ClickableAssignees from "./ClickableAssignees";
import AgentResponseDialog from "./AgentResponseDialog";
import TaskDetailsDialog from "./TaskDetailsDialog";
import TaskEditDialog from "./TaskEditDialog";
import AgentAssignmentDialog from "./AgentAssignmentDialog";
import TaskContextDialog from "./TaskContextDialog";
import TaskCompleteDialog from "./TaskCompleteDialog";
import DeleteConfirmDialog from "./DeleteConfirmDialog";

interface TaskListProps {
  projectId: string;
  taskTreeId: string;
  onTasksChanged?: () => void; // Callback when tasks are modified
}

const TaskList: React.FC<TaskListProps> = ({ projectId, taskTreeId, onTasksChanged }) => {
  // Core state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);

  // Agent data
  const [agents, setAgents] = useState<any[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);

  // Dependencies
  const [dependencyTitles, setDependencyTitles] = useState<Record<string, string>>({});
  const [hoveredDependency, setHoveredDependency] = useState<string | null>(null);

  // Dialog states
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [showTaskDetailsDialog, setShowTaskDetailsDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [showAgentResponse, setShowAgentResponse] = useState(false);
  const [showTaskContext, setShowTaskContext] = useState(false);
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Dialog-specific state
  const [currentAgentResponse, setCurrentAgentResponse] = useState<{
    agent: string;
    task: string;
    response?: any;
    error?: string;
    timestamp: string;
  } | null>(null);
  const [taskContext, setTaskContext] = useState<any>(null);
  const [loadingContext, setLoadingContext] = useState(false);

  // Refresh function - optimized to only load essential data
  const refreshTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const taskList = await listTasks({ git_branch_id: taskTreeId });
      setTasks(taskList);
      
      // Build dependency titles map from tasks we already have (lightweight operation)
      const depTitles: Record<string, string> = {};
      const taskMap: Record<string, Task> = {};
      
      // First pass: create a map of all tasks by ID
      taskList.forEach(task => {
        taskMap[task.id] = task;
      });
      
      // Second pass: resolve dependency titles from the task map
      taskList.forEach(task => {
        if (task.dependencies && task.dependencies.length > 0) {
          task.dependencies.forEach((depId: string) => {
            // Try to get title from tasks we already have
            if (taskMap[depId]) {
              depTitles[depId] = taskMap[depId].title;
            } else {
              // If dependency is not in current task list, show truncated ID
              depTitles[depId] = depId.substring(0, 8) + '...';
            }
          });
        }
      });
      
      setDependencyTitles(depTitles);
      
      // Don't load agents here - load them only when needed
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Load tasks and dependencies
  useEffect(() => {
    refreshTasks();
  }, [projectId, taskTreeId]);

  // Lazy load agents only when assignment dialog is opened
  const loadAgentsIfNeeded = async () => {
    if (agents.length === 0) {
      try {
        const [projectAgents, availableAgentsList] = await Promise.all([
          listAgents(projectId),
          getAvailableAgents()
        ]);
        setAgents(projectAgents);
        setAvailableAgents(availableAgentsList);
      } catch (e) {
        console.error('Error fetching agents:', e);
      }
    }
  };

  // Task expansion
  const toggleTaskExpansion = (taskId: string) => {
    setExpandedTasks(prev => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  // Task Details Dialog
  const openTaskDetailsDialog = (task: Task) => {
    setSelectedTask(task);
    setShowTaskDetailsDialog(true);
  };

  const closeTaskDetailsDialog = () => {
    setShowTaskDetailsDialog(false);
    setSelectedTask(null);
  };

  // Task Edit Dialog
  const openEditDialog = (task: Task) => {
    setSelectedTask(task);
    setShowEditDialog(true);
  };

  const closeEditDialog = () => {
    setShowEditDialog(false);
    setSelectedTask(null);
  };

  const handleTaskEdit = async (updates: Partial<Task>) => {
    if (!selectedTask) return;
    
    setSaving(true);
    setError(null);
    try {
      const result = await updateTask(selectedTask.id, updates);
      
      if (result) {
        closeEditDialog();
        // Refresh tasks list
        const updatedTasks = await listTasks({ git_branch_id: taskTreeId });
        setTasks(updatedTasks);
      } else {
        setError("Failed to update task - no response from server");
      }
    } catch (e: any) {
      setError(e.message || "Failed to update task");
    } finally {
      setSaving(false);
    }
  };

  // Task Create handlers
  const openCreateDialog = () => {
    setSelectedTask(null);
    setShowCreateDialog(true);
  };

  const closeCreateDialog = () => {
    setShowCreateDialog(false);
    setSelectedTask(null);
  };

  const handleTaskCreate = async (taskData: Partial<Task>) => {
    setSaving(true);
    setError(null);
    try {
      const newTask = await createTask({
        ...taskData,
        git_branch_id: taskTreeId
      });
      
      if (newTask) {
        closeCreateDialog();
        // Refresh tasks list
        await refreshTasks();
        // Notify parent to refresh project list (updates task counter)
        onTasksChanged?.();
      } else {
        setError("Failed to create task - no response from server");
      }
    } catch (e: any) {
      setError(e.message || "Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  // Agent Assignment Dialog - lazy load agents
  const openAssignDialog = async (task: Task) => {
    setSelectedTask(task);
    await loadAgentsIfNeeded(); // Load agents only when needed
    setShowAssignDialog(true);
  };

  const closeAssignDialog = () => {
    setShowAssignDialog(false);
    setSelectedTask(null);
  };

  const handleAgentAssignment = async (selectedAgents: string[]) => {
    if (!selectedTask) return;
    
    setSaving(true);
    console.log('Assigning agents to task:', selectedTask.id, 'Agents:', selectedAgents);
    
    try {
      const updated = await updateTask(selectedTask.id, { assignees: selectedAgents });
      console.log('Assignment result:', updated);
      
      if (updated) {
        setTasks(prevTasks => 
          prevTasks.map(t => t.id === selectedTask.id ? { ...t, assignees: selectedAgents } : t)
        );
        closeAssignDialog();
      }
    } catch (e) {
      console.error('Error assigning agents:', e);
      alert(`Failed to assign agents: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  // Agent Response Dialog
  const handleCallAgent = async (agentName: string, task: Task | Subtask) => {
    try {
      console.log('Calling agent:', agentName, 'for task:', task.title);
      const result = await callAgent(agentName);
      
      // Set response data and show dialog
      setCurrentAgentResponse({
        agent: agentName,
        task: task.title,
        response: result,
        timestamp: new Date().toISOString()
      });
      setShowAgentResponse(true);
      
    } catch (e) {
      console.error('Error calling agent:', e);
      
      // Set error data and show dialog
      setCurrentAgentResponse({
        agent: agentName,
        task: task.title,
        error: e instanceof Error ? e.message : 'Unknown error',
        timestamp: new Date().toISOString()
      });
      setShowAgentResponse(true);
    }
  };

  const closeAgentResponseDialog = () => {
    setShowAgentResponse(false);
    setCurrentAgentResponse(null);
  };

  // Task Context Dialog
  const handleViewContext = async (task: Task) => {
    setSelectedTask(task);
    setLoadingContext(true);
    setShowTaskContext(true);
    
    try {
      const context = await getTaskContext(task.id);
      if (!context) {
        // If context doesn't exist, show a message
        setTaskContext({
          message: "No context available for this task",
          info: "This task may have been created before context tracking was enabled, or the context has not been created yet.",
          task_id: task.id,
          suggestions: [
            "Complete the task with a summary to create context",
            "Update the task to trigger context creation"
          ]
        });
      } else {
        setTaskContext(context);
      }
    } catch (e) {
      console.error('Error fetching task context:', e);
      setTaskContext({
        error: true,
        message: "Failed to load context",
        details: e instanceof Error ? e.message : String(e)
      });
    } finally {
      setLoadingContext(false);
    }
  };

  const closeTaskContextDialog = () => {
    setShowTaskContext(false);
    setSelectedTask(null);
    setTaskContext(null);
  };

  // Task Complete Dialog handlers
  const openCompleteDialog = (task: Task) => {
    setSelectedTask(task);
    setShowCompleteDialog(true);
  };

  const closeCompleteDialog = () => {
    setShowCompleteDialog(false);
    setSelectedTask(null);
  };

  const handleTaskComplete = async (completedTask: Task) => {
    // Update the task in the list
    setTasks(prevTasks => 
      prevTasks.map(t => t.id === completedTask.id ? { ...t, status: 'done' } : t)
    );
    closeCompleteDialog();
    // Optionally refresh the entire list to get updated data
    await refreshTasks();
    // Notify parent to refresh project list (doesn't change counter but keeps consistency)
    onTasksChanged?.();
  };

  // Delete handlers
  const openDeleteDialog = (task: Task) => {
    setSelectedTask(task);
    setShowDeleteDialog(true);
  };

  const closeDeleteDialog = () => {
    setShowDeleteDialog(false);
    setSelectedTask(null);
  };

  const handleTaskDelete = async () => {
    if (!selectedTask) return;
    
    setDeleting(true);
    setError(null);
    
    // Store the task data for potential restoration
    const taskToDelete = selectedTask;
    const taskIdToDelete = selectedTask.id;
    const previousTasks = tasks;
    
    // Optimistic update - remove task immediately from UI
    setTasks(prevTasks => prevTasks.filter(t => t.id !== taskIdToDelete));
    
    // Close dialog immediately for better UX
    closeDeleteDialog();
    
    try {
      await deleteTask(taskIdToDelete);
      
      // Success! The task is already removed from UI, just notify parent
      console.log('Task deleted successfully, calling onTasksChanged callback...');
      onTasksChanged?.();
      
      // Don't refresh here - the optimistic update already handled the UI
    } catch (e: any) {
      // On error, restore the original task list
      console.error('Failed to delete task, restoring to list:', e);
      setError(e.message || "Failed to delete task");
      
      // Restore the previous task list
      setTasks(previousTasks);
    } finally {
      setDeleting(false);
    }
  };

  // Search handlers
  const handleTaskSelectFromSearch = (task: Task) => {
    // Expand the task if it has subtasks
    if (task.subtasks && task.subtasks.length > 0) {
      setExpandedTasks(prev => ({ ...prev, [task.id]: true }));
    }
    // Scroll to the task - this would require adding refs to task rows
    // For now, just open the task details
    openTaskDetailsDialog(task);
  };

  const handleSubtaskSelectFromSearch = (subtask: Subtask, parentTask: Task) => {
    // Expand the parent task to show subtasks
    setExpandedTasks(prev => ({ ...prev, [parentTask.id]: true }));
    // For now, open parent task details
    openTaskDetailsDialog(parentTask);
  };

  if (loading) return <div>Loading tasks...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <>
      <div className="space-y-4">
        {/* Search Bar */}
        <div className="w-full">
          <TaskSearch
            projectId={projectId}
            taskTreeId={taskTreeId}
            onTaskSelect={handleTaskSelectFromSearch}
            onSubtaskSelect={handleSubtaskSelectFromSearch}
          />
        </div>
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Tasks</h2>
          <div className="flex gap-2">
            <ShimmerButton
              onClick={openCreateDialog}
              size="sm"
              variant="default"
              className="flex items-center gap-1"
            >
              <Plus className="w-4 h-4" />
              New Task
            </ShimmerButton>
            <RefreshButton 
              onClick={refreshTasks} 
              loading={loading}
              size="sm"
            />
          </div>
        </div>
      </div>
      {/* Desktop Table View */}
      <div className="hidden lg:block overflow-x-auto">
        <Table>
        <TableHeader>
          <TableRow>
            <TableHead style={{ width: '50px' }}></TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Priority</TableHead>
            <TableHead>Dependencies</TableHead>
            <TableHead>Assignees</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map(task => (
            <React.Fragment key={task.id}>
              <TableRow className={hoveredDependency === task.id ? "theme-context-progress transition-colors" : ""}>
                <TableCell>
                  <ShimmerButton variant="ghost" size="icon" onClick={() => toggleTaskExpansion(task.id)}>
                    {expandedTasks[task.id] ? <Minus /> : <Plus />}
                  </ShimmerButton>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{task.title}</span>
                    {task.subtasks && task.subtasks.length > 0 && (
                      <ShimmerBadge variant="outline" className="text-xs ml-1">
                        {Array.isArray(task.subtasks) ? task.subtasks.length : 0}
                      </ShimmerBadge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <HolographicStatusBadge status={task.status as any} />
                </TableCell>
                <TableCell>
                  <HolographicPriorityBadge priority={task.priority as any} />
                </TableCell>
                <TableCell>
                  {task.dependencies && task.dependencies.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {task.dependencies.map((dep: string, index: number) => (
                        <ShimmerBadge 
                          key={index} 
                          variant="outline" 
                          className="text-xs flex items-center gap-1 cursor-pointer hover:bg-yellow-200"
                          title={`Depends on: ${dependencyTitles[dep] || dep}`}
                          onMouseEnter={() => setHoveredDependency(dep)}
                          onMouseLeave={() => setHoveredDependency(null)}
                        >
                          <Link className="w-3 h-3" />
                          {dependencyTitles[dep] ? 
                            (dependencyTitles[dep].length > 20 ? 
                              dependencyTitles[dep].substring(0, 20) + '...' : 
                              dependencyTitles[dep]
                            ) : 
                            dep.substring(0, 8) + '...'
                          }
                        </ShimmerBadge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">None</span>
                  )}
                </TableCell>
                <TableCell>
                  <ClickableAssignees
                    assignees={task.assignees || []}
                    task={task}
                    onAgentClick={handleCallAgent}
                    variant="secondary"
                  />
                </TableCell>
                <TableCell>
                  <ShimmerButton 
                    variant="ghost" 
                    size="icon"
                    onClick={() => openTaskDetailsDialog(task)}
                    title="View task details"
                  >
                    <Eye />
                  </ShimmerButton>
                  <ShimmerButton 
                    variant="ghost" 
                    size="icon"
                    onClick={() => handleViewContext(task)}
                    title="View task context"
                  >
                    <FileText />
                  </ShimmerButton>
                  <ShimmerButton 
                    variant="ghost" 
                    size="icon"
                    onClick={() => openAssignDialog(task)}
                    title="Assign agents"
                  >
                    <Users />
                  </ShimmerButton>
                  <ShimmerButton 
                    variant="ghost" 
                    size="icon" 
                    title="Edit task"
                    onClick={() => openEditDialog(task)}
                  >
                    <Pencil />
                  </ShimmerButton>
                  {task.status !== 'done' && (
                    <ShimmerButton 
                      variant="ghost" 
                      size="icon" 
                      title="Complete task"
                      onClick={() => openCompleteDialog(task)}
                    >
                      <Check />
                    </ShimmerButton>
                  )}
                  <ShimmerButton 
                    variant="ghost" 
                    size="icon" 
                    title="Delete task"
                    onClick={() => openDeleteDialog(task)}
                  >
                    <Trash2 />
                  </ShimmerButton>
                </TableCell>
              </TableRow>
              {expandedTasks[task.id] && (
                <TableRow>
                  <TableCell colSpan={7}>
                    <SubtaskList projectId={projectId} taskTreeId={taskTreeId} parentTaskId={task.id} />
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
        </Table>
      </div>

      {/* Mobile Card View */}
      <div className="block lg:hidden space-y-3">
        {tasks.map(task => (
          <div key={task.id} className={`theme-card hover:theme-surface-hover rounded-lg p-4 transition-colors ${hoveredDependency === task.id ? "theme-context-progress" : ""}`}>
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1 pr-2">
                <h3 className="font-semibold text-base flex items-center gap-2 flex-wrap">
                  {task.title}
                  {task.subtasks && task.subtasks.length > 0 && (
                    <ShimmerBadge variant="outline" className="text-xs">
                      {Array.isArray(task.subtasks) ? task.subtasks.length : 0} subtasks
                    </ShimmerBadge>
                  )}
                </h3>
              </div>
              <ShimmerButton 
                variant="ghost" 
                size="icon"
                className="shrink-0"
                onClick={() => toggleTaskExpansion(task.id)}
              >
                {expandedTasks[task.id] ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              </ShimmerButton>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-3">
              <HolographicStatusBadge status={task.status as any} size="sm" />
              <HolographicPriorityBadge priority={task.priority as any} size="sm" />
            </div>

            {task.dependencies && task.dependencies.length > 0 && (
              <div className="mb-3">
                <p className="text-sm text-muted-foreground mb-1">Dependencies:</p>
                <div className="flex flex-wrap gap-1">
                  {task.dependencies.map((dep: string, index: number) => (
                    <ShimmerBadge 
                      key={index} 
                      variant="outline" 
                      className="text-xs flex items-center gap-1"
                      title={`Depends on: ${dependencyTitles[dep] || dep}`}
                    >
                      <Link className="w-3 h-3" />
                      {dependencyTitles[dep] ? 
                        (dependencyTitles[dep].length > 15 ? 
                          dependencyTitles[dep].substring(0, 15) + '...' : 
                          dependencyTitles[dep]
                        ) : 
                        dep.substring(0, 6) + '...'
                      }
                    </ShimmerBadge>
                  ))}
                </div>
              </div>
            )}

            {(task.assignees && task.assignees.length > 0) && (
              <div className="mb-3">
                <p className="text-sm text-muted-foreground mb-1">Assignees:</p>
                <ClickableAssignees
                  assignees={task.assignees || []}
                  task={task}
                  onAgentClick={handleCallAgent}
                  variant="secondary"
                />
              </div>
            )}

            <div className="flex gap-1 justify-end flex-wrap">
              <ShimmerButton 
                variant="ghost" 
                size="sm"
                onClick={() => openTaskDetailsDialog(task)}
              >
                <Eye className="h-4 w-4" />
              </ShimmerButton>
              <ShimmerButton 
                variant="ghost" 
                size="sm"
                onClick={() => handleViewContext(task)}
              >
                <FileText className="h-4 w-4" />
              </ShimmerButton>
              <ShimmerButton 
                variant="ghost" 
                size="sm"
                onClick={() => openAssignDialog(task)}
              >
                <Users className="h-4 w-4" />
              </ShimmerButton>
              <ShimmerButton 
                variant="ghost" 
                size="sm"
                onClick={() => openEditDialog(task)}
              >
                <Pencil className="h-4 w-4" />
              </ShimmerButton>
              {task.status !== 'done' && (
                <ShimmerButton 
                  variant="ghost" 
                  size="sm"
                  onClick={() => openCompleteDialog(task)}
                  title="Complete task"
                >
                  <Check className="h-4 w-4" />
                </ShimmerButton>
              )}
              <ShimmerButton 
                variant="ghost" 
                size="sm"
                onClick={() => openDeleteDialog(task)}
                title="Delete task"
              >
                <Trash2 className="h-4 w-4" />
              </ShimmerButton>
            </div>

            {expandedTasks[task.id] && (
              <div className="mt-4 pt-4 border-t">
                <SubtaskList projectId={projectId} taskTreeId={taskTreeId} parentTaskId={task.id} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* All Dialog Components */}
      <TaskDetailsDialog
        open={showTaskDetailsDialog}
        onOpenChange={setShowTaskDetailsDialog}
        task={selectedTask}
        onClose={closeTaskDetailsDialog}
        onAgentClick={handleCallAgent}
      />

      <TaskEditDialog
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        task={selectedTask}
        onClose={closeEditDialog}
        onSave={handleTaskEdit}
        saving={saving}
      />

      <TaskEditDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        task={null}
        onClose={closeCreateDialog}
        onSave={handleTaskCreate}
        saving={saving}
      />

      <AgentAssignmentDialog
        open={showAssignDialog}
        onOpenChange={setShowAssignDialog}
        task={selectedTask}
        onClose={closeAssignDialog}
        onAssign={handleAgentAssignment}
        agents={agents}
        availableAgents={availableAgents}
        saving={saving}
      />

      <AgentResponseDialog
        open={showAgentResponse}
        onOpenChange={setShowAgentResponse}
        agentResponse={currentAgentResponse}
        onClose={closeAgentResponseDialog}
      />

      <TaskContextDialog
        open={showTaskContext}
        onOpenChange={setShowTaskContext}
        task={selectedTask}
        context={taskContext}
        onClose={closeTaskContextDialog}
        loading={loadingContext}
      />

      <TaskCompleteDialog
        open={showCompleteDialog}
        onOpenChange={setShowCompleteDialog}
        task={selectedTask}
        onClose={closeCompleteDialog}
        onComplete={handleTaskComplete}
      />

      <DeleteConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleTaskDelete}
        title="Delete Task"
        description="Are you sure you want to delete this task? This action cannot be undone."
        itemName={selectedTask?.title}
        isDeleting={deleting}
      />
    </>
  );
};

export default TaskList;