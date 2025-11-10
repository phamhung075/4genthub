import React, { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Check, FileText } from "lucide-react";
import { useSubtaskMutations } from "../hooks/useSubtasks";

interface SubtaskCompleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subtask: any | null;
  parentTaskId: string;
  onClose: () => void;
  onComplete: (subtask: any) => void;
}

export const SubtaskCompleteDialog: React.FC<SubtaskCompleteDialogProps> = ({
  open,
  onOpenChange,
  subtask,
  parentTaskId,
  onClose,
  onComplete,
}) => {
  const [completionSummary, setCompletionSummary] = useState("");
  const [impactOnParent, setImpactOnParent] = useState("");
  const [challengesOvercome, setChallengesOvercome] = useState("");
  const [isCompleted, setIsCompleted] = useState(false);

  // Use React Query mutation hook
  const { completeSubtaskAsync, isCompleting, completeError } = useSubtaskMutations();

  // Validation - match backend requirement (minimum 10 characters for detailed summary)
  const MIN_SUMMARY_LENGTH = 10;
  const isValidSummary = completionSummary.trim().length >= MIN_SUMMARY_LENGTH;

  // Reset form when subtask changes
  React.useEffect(() => {
    if (subtask) {
      setCompletionSummary("");
      setImpactOnParent("");
      setChallengesOvercome("");
      setIsCompleted(false);
    }
  }, [subtask]);

  const handleComplete = async () => {
    console.log('[SubtaskCompleteDialog] handleComplete called', {
      hasSubtask: !!subtask,
      isValidSummary,
      subtaskId: subtask?.id,
      summaryLength: completionSummary.trim().length
    });

    if (!subtask || !isValidSummary) {
      console.warn('[SubtaskCompleteDialog] Validation failed', {
        hasSubtask: !!subtask,
        isValidSummary
      });
      return;
    }

    try {
      // Build completion notes string
      let notes = completionSummary;
      if (impactOnParent.trim()) {
        notes += `\n\nImpact on Parent: ${impactOnParent}`;
      }
      if (challengesOvercome.trim()) {
        notes += `\n\nChallenges Overcome:\n${challengesOvercome}`;
      }

      console.log('[SubtaskCompleteDialog] Calling completeSubtaskAsync', {
        subtaskId: subtask.id,
        notesLength: notes.length
      });

      const result = await completeSubtaskAsync({
        subtaskId: subtask.id,
        completion_notes: notes
      });

      console.log('[SubtaskCompleteDialog] API call succeeded', {
        result,
        hasResult: !!result
      });

      // Only proceed if API call succeeded
      if (result) {
        console.log('[SubtaskCompleteDialog] Calling onComplete and onClose');
        // Hide button immediately to prevent multiple clicks
        setIsCompleted(true);
        onComplete(result);
        // Close dialog only after successful completion
        onClose();
      } else {
        console.error('[SubtaskCompleteDialog] Result is null/undefined - API call might have failed silently');
      }
    } catch (e: any) {
      // Error is handled by the mutation hook and displayed in UI
      console.error('[SubtaskCompleteDialog] Failed to complete subtask:', {
        error: e,
        message: e?.message,
        response: e?.response?.data
      });
      // Don't close dialog - let user see the error and retry
    }
  };

  const handleCancel = () => {
    setCompletionSummary("");
    setImpactOnParent("");
    setChallengesOvercome("");
    setIsCompleted(false);
    // Call onClose for manual close action
    onClose();
  };

  // Handle dialog close from built-in triggers (X button, ESC, backdrop click)
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Clean up form state
      setCompletionSummary("");
      setImpactOnParent("");
      setChallengesOvercome("");
      setIsCompleted(false);
      // Call both callbacks to ensure parent state updates
      onOpenChange(false);
      onClose();
    }
  };

  if (!subtask) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Complete Subtask</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Subtask Information */}
          <div className="bg-muted/50 dark:bg-muted/30 p-3 rounded border border-border">
            <h4 className="font-medium text-sm mb-1 text-foreground">Subtask: {subtask.title}</h4>
            {subtask.description && (
              <p className="text-xs text-muted-foreground">{subtask.description}</p>
            )}
          </div>

          {/* Completion Summary */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Completion Summary * (minimum {MIN_SUMMARY_LENGTH} characters)
            </label>
            <textarea
              className={`w-full p-2 bg-background text-foreground rounded-md resize-vertical focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                completionSummary.length > 0 && !isValidSummary
                  ? 'border border-destructive'
                  : 'border border-input'
              }`}
              placeholder="Describe what was accomplished in detail..."
              value={completionSummary}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCompletionSummary(e.target.value)}
              disabled={isCompleting}
              rows={3}
              autoFocus
            />
            <div className="flex justify-between items-center mt-1">
              <p className={`text-xs ${
                completionSummary.length > 0 && !isValidSummary
                  ? 'text-destructive'
                  : 'text-muted-foreground'
              }`}>
                {completionSummary.length > 0 && !isValidSummary
                  ? `Need ${MIN_SUMMARY_LENGTH - completionSummary.trim().length} more characters for a detailed summary`
                  : 'Provide a detailed summary of what was accomplished'}
              </p>
              <p className={`text-xs ${
                isValidSummary
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-muted-foreground'
              }`}>
                {completionSummary.trim().length}/{MIN_SUMMARY_LENGTH}
              </p>
            </div>
          </div>

          {/* Impact on Parent */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Impact on Parent Task (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-input bg-background text-foreground rounded-md resize-vertical focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="How does completing this subtask affect the parent task?"
              value={impactOnParent}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setImpactOnParent(e.target.value)}
              disabled={isCompleting}
              rows={2}
            />
          </div>

          {/* Challenges Overcome */}
          <div>
            <label className="text-sm font-medium mb-2 block text-foreground">
              Challenges Overcome (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-input bg-background text-foreground rounded-md resize-vertical focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="List any challenges faced and overcome (one per line)..."
              value={challengesOvercome}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setChallengesOvercome(e.target.value)}
              disabled={isCompleting}
              rows={2}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Enter each challenge on a new line
            </p>
          </div>

          {/* Info Message */}
          <div className="bg-primary/10 dark:bg-primary/20 p-3 rounded-md flex gap-2 border border-primary/20">
            <FileText className="w-4 h-4 text-primary mt-0.5" />
            <div className="text-sm text-foreground">
              <p className="font-medium">Auto Progress Update</p>
              <p className="text-xs mt-1 text-muted-foreground">
                Completing this subtask will automatically update the parent task's progress.
              </p>
            </div>
          </div>

          {/* Error Display */}
          {completeError && (
            <div className="bg-destructive/10 dark:bg-destructive/20 border border-destructive/30 text-destructive px-3 py-2 rounded-md text-sm">
              {completeError.message || 'Failed to complete subtask'}
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isCompleting || isCompleted}>
            Cancel
          </Button>
          {!isCompleted && (
            <Button
              variant="default"
              onClick={handleComplete}
              disabled={isCompleting || !isValidSummary}
            >
              {isCompleting ? (
                <>
                  <Check className="w-4 h-4 animate-spin mr-2" />
                  Completing...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Complete Subtask
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SubtaskCompleteDialog;