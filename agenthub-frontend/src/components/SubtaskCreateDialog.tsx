import React, { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Plus, FileText } from "lucide-react";
import { Subtask } from "../api";
import { useSubtaskMutations } from "../hooks/useSubtasks";

interface SubtaskCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  parentTaskId: string;
  onClose: () => void;
  onCreated: (subtask: Subtask) => void;
}

const SubtaskCreateDialog: React.FC<SubtaskCreateDialogProps> = ({
  open,
  onOpenChange,
  parentTaskId,
  onClose,
  onCreated,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  // Use React Query mutation hook
  const { createSubtask, isCreating, createError } = useSubtaskMutations();

  // Reset form when dialog opens/closes
  React.useEffect(() => {
    if (open) {
      setTitle("");
      setDescription("");
    }
  }, [open]);

  const handleCreate = async () => {
    if (!title.trim()) {
      return;
    }

    try {
      const result = await createSubtask({
        taskId: parentTaskId,
        subtask: {
          title: title.trim(),
          description: description.trim() || undefined,
        }
      });

      if (result) {
        onCreated(result);
        onClose();
      }
    } catch (e: any) {
      // Error is already handled by the mutation hook
      console.error('Failed to create subtask:', e);
    }
  };

  const handleCancel = () => {
    setTitle("");
    setDescription("");
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      handleCreate();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create New Subtask</DialogTitle>
        </DialogHeader>

        <div className="space-y-4" onKeyDown={handleKeyDown}>
          {/* Title Field */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Title *
            </label>
            <Input
              placeholder="Enter subtask title..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isCreating}
              autoFocus
              className="w-full"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide a clear, descriptive title for the subtask
            </p>
          </div>

          {/* Description Field */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Description (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical theme-input"
              placeholder="Describe the subtask in detail..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isCreating}
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide additional context and requirements for the subtask
            </p>
          </div>

          {/* Info Message */}
          <div className="bg-blue-50 dark:bg-blue-950/30 p-3 rounded-md flex gap-2">
            <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-200">
              <p className="font-medium">Auto Configuration</p>
              <p className="text-xs mt-1">
                The subtask will be created with default status "todo" and medium priority.
                You can edit these settings after creation.
              </p>
            </div>
          </div>

          {/* Keyboard Shortcut Hint */}
          <div className="text-xs text-muted-foreground">
            <strong>Tip:</strong> Press Ctrl+Enter to create the subtask quickly
          </div>

          {/* Error Display */}
          {createError && (
            <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-3 py-2 rounded-md text-sm">
              {createError.message || 'Failed to create subtask'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleCreate}
            disabled={isCreating || !title.trim()}
          >
            {isCreating ? (
              <>
                <Plus className="w-4 h-4 animate-spin mr-2" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Create Subtask
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SubtaskCreateDialog;