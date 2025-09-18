import React, { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Plus, FileText } from "lucide-react";
import { createSubtask, Subtask } from "../api";

interface SubtaskCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  parentTaskId: string;
  onClose: () => void;
  onCreated: (subtask: Subtask) => void;
}

export const SubtaskCreateDialog: React.FC<SubtaskCreateDialogProps> = ({
  open,
  onOpenChange,
  parentTaskId,
  onClose,
  onCreated,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes
  React.useEffect(() => {
    if (open) {
      setTitle("");
      setDescription("");
      setError(null);
    }
  }, [open]);

  const handleCreate = async () => {
    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const result = await createSubtask(parentTaskId, {
        title: title.trim(),
        description: description.trim() || undefined,
      });

      if (result) {
        onCreated(result);
        onClose();
      } else {
        setError("Failed to create subtask");
      }
    } catch (e: any) {
      setError(e.message || "Failed to create subtask");
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = () => {
    setTitle("");
    setDescription("");
    setError(null);
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
              disabled={creating}
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
              disabled={creating}
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
          {error && (
            <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-3 py-2 rounded-md text-sm">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={creating}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleCreate}
            disabled={creating || !title.trim()}
          >
            {creating ? (
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