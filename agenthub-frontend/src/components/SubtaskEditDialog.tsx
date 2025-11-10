import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Save, FileText, Users } from "lucide-react";
import { Subtask, getAvailableAgents, listAgents } from "../api";
import { useSubtaskMutations } from "../hooks/useSubtasks";
import AgentAssignmentDialog from "./AgentAssignmentDialog";

interface SubtaskEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subtask: Subtask;
  parentTaskId: string;
  onClose: () => void;
  onUpdated?: (subtask: Subtask) => void;
}

export const SubtaskEditDialog: React.FC<SubtaskEditDialogProps> = ({
  open,
  onOpenChange,
  subtask,
  parentTaskId,
  onClose,
  onUpdated,
}) => {
  // Initialize state with subtask data
  const [title, setTitle] = useState(subtask.title || "");
  const [description, setDescription] = useState(subtask.description || "");
  const [status, setStatus] = useState<string>(subtask.status || "todo");
  const [priority, setPriority] = useState<string>(subtask.priority || "medium");
  const [assignees, setAssignees] = useState<string[]>(subtask.assignees || []);

  // Agent assignment dialog state
  const [agentDialogOpen, setAgentDialogOpen] = useState(false);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);
  const [projectAgents, setProjectAgents] = useState<any[]>([]);

  // Use React Query mutation hook
  const { updateSubtaskAsync, isUpdating, updateError } = useSubtaskMutations();

  // Pre-fill form when dialog opens or subtask changes
  useEffect(() => {
    if (open && subtask) {
      setTitle(subtask.title || "");
      setDescription(subtask.description || "");
      setStatus(subtask.status || "todo");
      setPriority(subtask.priority || "medium");
      setAssignees(subtask.assignees || []);
    }
  }, [open, subtask]);

  // Load available agents when dialog opens
  useEffect(() => {
    if (open) {
      Promise.all([
        listAgents(parentTaskId).catch(() => []),
        getAvailableAgents().catch(() => [])
      ]).then(([projAgents, availAgents]) => {
        setProjectAgents(projAgents);
        setAvailableAgents(availAgents);
      });
    }
  }, [open, parentTaskId]);

  const handleUpdate = async () => {
    if (!title.trim()) {
      return;
    }

    try {
      const updates: Partial<Subtask> = {
        title: title.trim(),
        description: description.trim() || undefined,
        status: status as any,
        priority: priority as any,
        assignees: assignees.length > 0 ? assignees : undefined,
      };

      const result = await updateSubtaskAsync({
        subtaskId: subtask.id,
        updates
      });

      if (onUpdated) {
        onUpdated(result);
      }
      onClose();
    } catch (e: any) {
      // Error is already handled by the mutation hook
      console.error('Failed to update subtask:', e);
    }
  };

  const handleAssignAgents = (selectedAgents: string[]) => {
    setAssignees(selectedAgents);
    setAgentDialogOpen(false);
  };

  const handleCancel = () => {
    // Reset to original values
    if (subtask) {
      setTitle(subtask.title || "");
      setDescription(subtask.description || "");
      setStatus(subtask.status || "todo");
      setPriority(subtask.priority || "medium");
      setAssignees(subtask.assignees || []);
    }
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      handleUpdate();
    }
  };

  // Check if form has changes
  const hasChanges =
    title !== (subtask.title || "") ||
    description !== (subtask.description || "") ||
    status !== (subtask.status || "todo") ||
    priority !== (subtask.priority || "medium") ||
    JSON.stringify(assignees.sort()) !== JSON.stringify((subtask.assignees || []).sort());

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Subtask</DialogTitle>
        </DialogHeader>

        <div className="space-y-4" onKeyDown={handleKeyDown}>
          {/* Title Field */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Title *
            </label>
            <Input
              placeholder="Enter subtask title..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUpdating}
              autoFocus
              className="w-full"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide a clear, descriptive title for the subtask
            </p>
          </div>

          {/* Description Field */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Description (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-input bg-background text-foreground rounded-md resize-vertical focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="Describe the subtask in detail..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isUpdating}
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide additional context and requirements for the subtask
            </p>
          </div>

          {/* Status Field */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Status
            </label>
            <select
              className="w-full p-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={isUpdating || subtask.status === 'done'}
            >
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="blocked">Blocked</option>
              <option value="review">Review</option>
              <option value="testing">Testing</option>
              <option value="done">Done</option>
            </select>
            {subtask.status === 'done' && (
              <p className="text-xs text-muted-foreground mt-1">
                Completed subtasks cannot change status. Use "Reopen" if needed.
              </p>
            )}
          </div>

          {/* Priority Field */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Priority
            </label>
            <select
              className="w-full p-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              disabled={isUpdating}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Assignees Field */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Assignees (Optional)
            </label>
            <Button
              type="button"
              variant="outline"
              onClick={() => setAgentDialogOpen(true)}
              disabled={isUpdating}
              className="w-full justify-start"
            >
              <Users className="w-4 h-4 mr-2" />
              {assignees.length > 0
                ? `${assignees.length} agent${assignees.length > 1 ? 's' : ''} assigned`
                : 'Assign agents to subtask'}
            </Button>
            {assignees.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {assignees.map((agent, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                  >
                    {agent}
                  </Badge>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Click to select agents from your project or the agent library
            </p>
          </div>

          {/* Info Message */}
          <div className="bg-primary/10 dark:bg-primary/20 p-3 rounded-md flex gap-2 border border-primary/20">
            <FileText className="w-4 h-4 text-primary mt-0.5" />
            <div className="text-sm text-foreground">
              <p className="font-medium">Update Changes</p>
              <p className="text-xs mt-1 text-muted-foreground">
                Changes will be saved immediately and reflected in the subtask list.
              </p>
            </div>
          </div>

          {/* Keyboard Shortcut Hint */}
          <div className="text-xs text-muted-foreground">
            <strong>Tip:</strong> Press Ctrl+Enter to save changes quickly
          </div>

          {/* Error Display */}
          {updateError && (
            <div className="bg-destructive/10 dark:bg-destructive/20 border border-destructive/30 text-destructive px-3 py-2 rounded-md text-sm">
              {updateError.message || 'Failed to update subtask'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isUpdating}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleUpdate}
            disabled={isUpdating || !title.trim() || !hasChanges}
          >
            {isUpdating ? (
              <>
                <Save className="w-4 h-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Agent Assignment Dialog */}
    <AgentAssignmentDialog
      open={agentDialogOpen}
      onOpenChange={setAgentDialogOpen}
      task={{ ...subtask, assignees } as any}
      onClose={() => setAgentDialogOpen(false)}
      onAssign={handleAssignAgents}
      agents={projectAgents}
      availableAgents={availableAgents}
      saving={false}
    />
    </>
  );
};

export default SubtaskEditDialog;
