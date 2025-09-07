import React from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Task } from "../api";

interface TaskEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  onClose: () => void;
  onSave: (updates: Partial<Task>) => void;
  saving?: boolean;
}

export const TaskEditDialog: React.FC<TaskEditDialogProps> = ({
  open,
  onOpenChange,
  task,
  onClose,
  onSave,
  saving = false
}) => {
  const [editForm, setEditForm] = React.useState({
    title: "",
    description: "",
    priority: "medium",
    status: "todo"
  });

  // Update form when task changes
  React.useEffect(() => {
    if (task) {
      setEditForm({
        title: task.title || "",
        description: task.description || "",
        priority: task.priority || "medium",
        status: task.status || "todo"
      });
    }
  }, [task]);

  const handleSave = () => {
    if (!editForm.title.trim()) return;
    onSave(editForm);
  };

  const handleCancel = () => {
    // Reset form to original task values
    if (task) {
      setEditForm({
        title: task.title || "",
        description: task.description || "",
        priority: task.priority || "medium",
        status: task.status || "todo"
      });
    }
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit Task</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* Title */}
          <div>
            <label className="text-sm font-medium mb-2 block">Title *</label>
            <Input
              placeholder="Task title"
              value={editForm.title}
              onChange={(e) => setEditForm(prev => ({ ...prev, title: e.target.value }))}
              disabled={saving}
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium mb-2 block">Description</label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical"
              placeholder="Task description"
              value={editForm.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
              disabled={saving}
              rows={3}
            />
          </div>

          {/* Priority */}
          <div>
            <label className="text-sm font-medium mb-2 block">Priority</label>
            <select
              className="w-full p-2 border border-gray-300 rounded-md"
              value={editForm.priority}
              onChange={(e) => setEditForm(prev => ({ ...prev, priority: e.target.value }))}
              disabled={saving}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="text-sm font-medium mb-2 block">Status</label>
            <select
              className="w-full p-2 border border-gray-300 rounded-md"
              value={editForm.status}
              onChange={(e) => setEditForm(prev => ({ ...prev, status: e.target.value }))}
              disabled={saving}
            >
              <option value="todo">Todo</option>
              <option value="in_progress">In Progress</option>
              <option value="review">Review</option>
              <option value="testing">Testing</option>
              <option value="done">Done</option>
              <option value="blocked">Blocked</option>
              <option value="cancelled">Cancelled</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={saving}>
            Cancel
          </Button>
          <Button 
            variant="default" 
            onClick={handleSave} 
            disabled={saving || !editForm.title.trim()}
          >
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskEditDialog;