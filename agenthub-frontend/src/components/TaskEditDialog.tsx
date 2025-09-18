import React, { useRef } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Task, getAvailableAgents } from "../api";
import { X } from "lucide-react";

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
    status: "todo",
    assignees: [] as string[]
  });
  const [availableAgents, setAvailableAgents] = React.useState<string[]>([]);
  const [showAgentDropdown, setShowAgentDropdown] = React.useState(false);
  const [agentSearch, setAgentSearch] = React.useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load available agents on mount
  React.useEffect(() => {
    getAvailableAgents().then(agents => {
      setAvailableAgents(agents);
    });
  }, []);

  // Handle click outside to close dropdown
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowAgentDropdown(false);
      }
    };

    if (showAgentDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showAgentDropdown]);

  // Update form when task changes
  React.useEffect(() => {
    if (task) {
      // Edit mode - populate with existing task data
      setEditForm({
        title: task.title || "",
        description: task.description || "",
        priority: task.priority || "medium",
        status: task.status || "todo",
        assignees: task.assignees || []
      });
    } else {
      // Create mode - reset to defaults
      setEditForm({
        title: "",
        description: "",
        priority: "medium",
        status: "todo",
        assignees: []
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
        status: task.status || "todo",
        assignees: task.assignees || []
      });
    }
    onClose();
  };

  const toggleAgent = (agent: string) => {
    setEditForm(prev => ({
      ...prev,
      assignees: prev.assignees.includes(agent)
        ? prev.assignees.filter(a => a !== agent)
        : [...prev.assignees, agent]
    }));
  };

  const removeAgent = (agent: string) => {
    setEditForm(prev => ({
      ...prev,
      assignees: prev.assignees.filter(a => a !== agent)
    }));
  };

  const filteredAgents = availableAgents.filter(agent =>
    agent.toLowerCase().includes(agentSearch.toLowerCase())
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{task ? 'Edit Task' : 'Create New Task'}</DialogTitle>
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
              className="w-full p-2 border border-border bg-background text-foreground rounded-md resize-vertical focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800"
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
              className="w-full p-2 border border-border bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800"
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
              className="w-full p-2 border border-border bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800"
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

          {/* Agent Assignment */}
          <div>
            <label className="text-sm font-medium mb-2 block">Assign Agents</label>

            {/* Selected agents */}
            {editForm.assignees.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {editForm.assignees.map(agent => (
                  <div
                    key={agent}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                  >
                    <span>{agent}</span>
                    <button
                      type="button"
                      onClick={() => removeAgent(agent)}
                      className="hover:bg-blue-200 dark:hover:bg-blue-800 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Agent search input */}
            <div className="relative" ref={dropdownRef}>
              <Input
                placeholder="Search and select agents..."
                value={agentSearch}
                onChange={(e) => setAgentSearch(e.target.value)}
                onFocus={() => setShowAgentDropdown(true)}
                disabled={saving}
              />

              {/* Agent dropdown */}
              {showAgentDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-background border border-border rounded-md shadow-lg max-h-60 overflow-auto">
                  {filteredAgents.length > 0 ? (
                    filteredAgents.map(agent => (
                      <div
                        key={agent}
                        className={`px-3 py-2 hover:bg-accent cursor-pointer flex items-center justify-between ${
                          editForm.assignees.includes(agent) ? 'bg-accent/50' : ''
                        }`}
                        onClick={() => toggleAgent(agent)}
                      >
                        <span className="text-sm">{agent}</span>
                        {editForm.assignees.includes(agent) && (
                          <span className="text-xs text-green-600 dark:text-green-400">✓ Selected</span>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      No agents found
                    </div>
                  )}
                  <div className="px-3 py-2 border-t border-border">
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setShowAgentDropdown(false)}
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}
            </div>
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
            {saving ? "Saving..." : task ? "Save Changes" : "Create Task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskEditDialog;