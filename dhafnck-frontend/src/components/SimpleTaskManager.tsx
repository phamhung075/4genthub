import { Check, ChevronRight, Eye, Pencil, Plus, Trash2, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import { createTask, deleteTask, listTasks, listSubtasks, Subtask, Task, updateTask } from "../api";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Separator } from "./ui/separator";

interface SimpleTaskManagerProps {
  projectId?: string;
  taskTreeId?: string;
}

const SimpleTaskManager: React.FC<SimpleTaskManagerProps> = ({ 
  projectId = "demo_project", 
  taskTreeId = "main" 
}) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDialog, setShowDialog] = useState<'create' | 'edit' | 'delete' | 'details' | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [subtasks, setSubtasks] = useState<Subtask[]>([]);
  const [loadingSubtasks, setLoadingSubtasks] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "medium"
  });
  const [saving, setSaving] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const taskList = await listTasks({ project_id: projectId, git_branch_name: taskTreeId });
      setTasks(taskList);
    } catch (err: any) {
      setError(err.message || "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [projectId, taskTreeId]);

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    
    setSaving(true);
    try {
      await createTask({
        title: form.title,
        description: form.description,
        priority: form.priority,
        project_id: projectId,
        git_branch_name: taskTreeId
      });
      setShowDialog(null);
      setForm({ title: "", description: "", priority: "medium" });
      fetchTasks();
    } catch (err: any) {
      setError(err.message || "Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async () => {
    if (!selectedTask || !form.title.trim()) return;
    
    setSaving(true);
    try {
      await updateTask(selectedTask.id, {
        title: form.title,
        description: form.description,
        priority: form.priority
      });
      setShowDialog(null);
      setSelectedTask(null);
      setForm({ title: "", description: "", priority: "medium" });
      fetchTasks();
    } catch (err: any) {
      setError(err.message || "Failed to update task");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedTask) return;
    
    setSaving(true);
    try {
      await deleteTask(selectedTask.id);
      setShowDialog(null);
      setSelectedTask(null);
      fetchTasks();
    } catch (err: any) {
      setError(err.message || "Failed to delete task");
    } finally {
      setSaving(false);
    }
  };

  const openCreateDialog = () => {
    setForm({ title: "", description: "", priority: "medium" });
    setShowDialog('create');
  };

  const openEditDialog = (task: Task) => {
    setSelectedTask(task);
    setForm({
      title: task.title,
      description: task.description || "",
      priority: task.priority || "medium"
    });
    setShowDialog('edit');
  };

  const openDeleteDialog = (task: Task) => {
    setSelectedTask(task);
    setShowDialog('delete');
  };

  const openDetailsDialog = async (task: Task) => {
    setSelectedTask(task);
    setShowDialog('details');
    setLoadingSubtasks(true);
    setSubtasks([]);
    
    try {
      const subtaskList = await listSubtasks(task.id);
      setSubtasks(subtaskList);
    } catch (err: any) {
      setError(err.message || "Failed to fetch subtasks");
    } finally {
      setLoadingSubtasks(false);
    }
  };

  const closeDialog = () => {
    setShowDialog(null);
    setSelectedTask(null);
    setSubtasks([]);
    setForm({ title: "", description: "", priority: "medium" });
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'destructive';
      case 'high': return 'default';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'outline';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'default';
      case 'in_progress': return 'secondary';
      case 'pending': return 'outline';
      case 'cancelled': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Task Manager</h2>
        <Button onClick={openCreateDialog} className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Task
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-8">
          <div className="text-muted-foreground">Loading tasks...</div>
        </div>
      )}

      {/* Tasks List */}
      {!loading && (
        <div className="space-y-3">
          {tasks.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <div className="text-muted-foreground">No tasks found</div>
                <Button onClick={openCreateDialog} className="mt-4">
                  Create your first task
                </Button>
              </CardContent>
            </Card>
          ) : (
            tasks.map((task) => (
              <Card key={task.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{task.title}</CardTitle>
                      {task.description && (
                        <p className="text-sm text-muted-foreground">{task.description}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openDetailsDialog(task)}
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEditDialog(task)}
                        title="Edit task"
                      >
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openDeleteDialog(task)}
                        title="Delete task"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex gap-2">
                    <Badge variant={getStatusColor(task.status)}>
                      {task.status?.replace('_', ' ') || 'pending'}
                    </Badge>
                    <Badge variant={getPriorityColor(task.priority)}>
                      {task.priority || 'medium'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog === 'create' || showDialog === 'edit'} onOpenChange={closeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {showDialog === 'create' ? 'Create New Task' : 'Edit Task'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Title</label>
              <Input
                placeholder="Enter task title"
                value={form.title}
                onChange={(e) => setForm(prev => ({ ...prev, title: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Input
                placeholder="Enter task description"
                value={form.description}
                onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Priority</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={form.priority}
                onChange={(e) => setForm(prev => ({ ...prev, priority: e.target.value }))}
                disabled={saving}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog} disabled={saving}>
              Cancel
            </Button>
            <Button 
              onClick={showDialog === 'create' ? handleCreate : handleEdit} 
              disabled={saving || !form.title.trim()}
            >
              {saving ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {showDialog === 'create' ? 'Creating...' : 'Updating...'}
                </div>
              ) : (
                <>
                  {showDialog === 'create' ? <Plus className="w-4 h-4 mr-2" /> : <Check className="w-4 h-4 mr-2" />}
                  {showDialog === 'create' ? 'Create' : 'Update'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDialog === 'delete'} onOpenChange={closeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Task</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>Are you sure you want to delete this task?</p>
            <p className="font-medium mt-2">"{selectedTask?.title}"</p>
            <p className="text-sm text-muted-foreground mt-1">This action cannot be undone.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog} disabled={saving}>
              Cancel
            </Button>
            <Button 
              variant="default" 
              onClick={handleDelete} 
              disabled={saving}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {saving ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Deleting...
                </div>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Task Details Dialog */}
      <Dialog open={showDialog === 'details'} onOpenChange={closeDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Task Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Task Information */}
            <div>
              <h3 className="text-lg font-semibold">{selectedTask?.title}</h3>
              {selectedTask?.description && (
                <p className="text-sm text-muted-foreground mt-1">{selectedTask.description}</p>
              )}
              <div className="flex gap-2 mt-2">
                <Badge variant={getStatusColor(selectedTask?.status || 'pending')}>
                  {selectedTask?.status?.replace('_', ' ') || 'pending'}
                </Badge>
                <Badge variant={getPriorityColor(selectedTask?.priority || 'medium')}>
                  {selectedTask?.priority || 'medium'}
                </Badge>
              </div>
            </div>

            <Separator />

            {/* Subtasks Section */}
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <ChevronRight className="w-4 h-4" />
                Subtasks {subtasks.length > 0 && `(${subtasks.length})`}
              </h4>
              
              {loadingSubtasks ? (
                <div className="text-center py-4">
                  <div className="text-sm text-muted-foreground">Loading subtasks...</div>
                </div>
              ) : subtasks.length === 0 ? (
                <div className="text-sm text-muted-foreground py-4 text-center">
                  No subtasks found for this task
                </div>
              ) : (
                <div className="space-y-2">
                  {subtasks.map((subtask, index) => (
                    <div key={subtask.id} className="border rounded-md p-3 hover:bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h5 className="font-medium text-sm">
                            {index + 1}. {subtask.title}
                          </h5>
                          {subtask.description && (
                            <p className="text-xs text-muted-foreground mt-1">{subtask.description}</p>
                          )}
                        </div>
                        <div className="flex gap-1 ml-2">
                          <Badge variant={getStatusColor(subtask.status)} className="text-xs">
                            {subtask.status?.replace('_', ' ') || 'pending'}
                          </Badge>
                          <Badge variant={getPriorityColor(subtask.priority)} className="text-xs">
                            {subtask.priority || 'medium'}
                          </Badge>
                        </div>
                      </div>
                      {/* Display additional subtask properties if available */}
                      {subtask.assignees && subtask.assignees.length > 0 && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Assignees: {Array.isArray(subtask.assignees) ? subtask.assignees.join(', ') : subtask.assignees}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Additional Task Details */}
            {selectedTask && (
              <div className="space-y-2 text-sm">
                <Separator />
                <div className="grid grid-cols-2 gap-2">
                  {selectedTask.estimated_effort && (
                    <div>
                      <span className="text-muted-foreground">Estimated Effort:</span> {selectedTask.estimated_effort}
                    </div>
                  )}
                  {selectedTask.due_date && (
                    <div>
                      <span className="text-muted-foreground">Due Date:</span> {new Date(selectedTask.due_date).toLocaleDateString()}
                    </div>
                  )}
                  {selectedTask.created_at && (
                    <div>
                      <span className="text-muted-foreground">Created:</span> {new Date(selectedTask.created_at).toLocaleDateString()}
                    </div>
                  )}
                  {selectedTask.updated_at && (
                    <div>
                      <span className="text-muted-foreground">Updated:</span> {new Date(selectedTask.updated_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
                {selectedTask.labels && selectedTask.labels.length > 0 && (
                  <div className="flex gap-1 items-center">
                    <span className="text-muted-foreground">Labels:</span>
                    {selectedTask.labels.map((label: string) => (
                      <Badge key={label} variant="outline" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SimpleTaskManager;