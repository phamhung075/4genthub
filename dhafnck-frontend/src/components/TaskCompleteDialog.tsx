import React, { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Check, FileText } from "lucide-react";
import { completeTask, Task } from "../api";

interface TaskCompleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  onClose: () => void;
  onComplete: (task: Task) => void;
}

export const TaskCompleteDialog: React.FC<TaskCompleteDialogProps> = ({
  open,
  onOpenChange,
  task,
  onClose,
  onComplete,
}) => {
  const [completionSummary, setCompletionSummary] = useState("");
  const [testingNotes, setTestingNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when task changes
  React.useEffect(() => {
    if (task) {
      setCompletionSummary("");
      setTestingNotes("");
      setError(null);
    }
  }, [task]);

  const handleComplete = async () => {
    if (!task || !completionSummary.trim()) {
      setError("Completion summary is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const result = await completeTask(task.id, completionSummary, testingNotes || undefined);
      
      if (result) {
        onComplete(result);
        onClose();
      } else {
        setError("Failed to complete task");
      }
    } catch (e: any) {
      setError(e.message || "Failed to complete task");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setCompletionSummary("");
    setTestingNotes("");
    setError(null);
    onClose();
  };

  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Complete Task</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Task Information */}
          <div className="bg-gray-50 p-3 rounded">
            <h4 className="font-medium text-sm mb-1">Task: {task.title}</h4>
            {task.description && (
              <p className="text-xs text-muted-foreground">{task.description}</p>
            )}
          </div>

          {/* Completion Summary */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Completion Summary *
            </label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical"
              placeholder="Describe what was accomplished in detail..."
              value={completionSummary}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCompletionSummary(e.target.value)}
              disabled={saving}
              rows={4}
              autoFocus
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide a detailed summary of what was accomplished
            </p>
          </div>

          {/* Testing Notes */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Testing Notes (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical"
              placeholder="Describe any testing performed..."
              value={testingNotes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTestingNotes(e.target.value)}
              disabled={saving}
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Include details about testing, validation, or verification performed
            </p>
          </div>

          {/* Info Message */}
          <div className="bg-blue-50 p-3 rounded-md flex gap-2">
            <FileText className="w-4 h-4 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium">Context will be automatically created</p>
              <p className="text-xs mt-1">
                The system will automatically create and update the task context when you complete this task.
              </p>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
              {error}
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={saving}>
            Cancel
          </Button>
          <Button 
            variant="default" 
            onClick={handleComplete} 
            disabled={saving || !completionSummary.trim()}
          >
            {saving ? (
              <>
                <Check className="w-4 h-4 animate-spin mr-2" />
                Completing...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Complete Task
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskCompleteDialog;