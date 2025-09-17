import React, { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Check, FileText } from "lucide-react";
import { completeSubtask } from "../api";

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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when subtask changes
  React.useEffect(() => {
    if (subtask) {
      setCompletionSummary("");
      setImpactOnParent("");
      setChallengesOvercome("");
      setError(null);
    }
  }, [subtask]);

  const handleComplete = async () => {
    if (!subtask || !completionSummary.trim()) {
      setError("Completion summary is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Parse challenges overcome into array if provided
      const challenges = challengesOvercome.trim()
        ? challengesOvercome.split('\n').filter(c => c.trim())
        : undefined;

      const result = await completeSubtask(
        parentTaskId,
        subtask.id,
        completionSummary,
        impactOnParent || undefined,
        challenges
      );
      
      if (result) {
        onComplete(result);
        onClose();
      } else {
        setError("Failed to complete subtask");
      }
    } catch (e: any) {
      setError(e.message || "Failed to complete subtask");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setCompletionSummary("");
    setImpactOnParent("");
    setChallengesOvercome("");
    setError(null);
    onClose();
  };

  if (!subtask) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Complete Subtask</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Subtask Information */}
          <div className="bg-gray-50 p-3 rounded">
            <h4 className="font-medium text-sm mb-1">Subtask: {subtask.title}</h4>
            {subtask.description && (
              <p className="text-xs text-muted-foreground">{subtask.description}</p>
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
              rows={3}
              autoFocus
            />
            <p className="text-xs text-muted-foreground mt-1">
              Provide a detailed summary of what was accomplished
            </p>
          </div>

          {/* Impact on Parent */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Impact on Parent Task (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical"
              placeholder="How does completing this subtask affect the parent task?"
              value={impactOnParent}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setImpactOnParent(e.target.value)}
              disabled={saving}
              rows={2}
            />
          </div>

          {/* Challenges Overcome */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Challenges Overcome (Optional)
            </label>
            <textarea
              className="w-full p-2 border border-gray-300 rounded-md resize-vertical"
              placeholder="List any challenges faced and overcome (one per line)..."
              value={challengesOvercome}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setChallengesOvercome(e.target.value)}
              disabled={saving}
              rows={2}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Enter each challenge on a new line
            </p>
          </div>

          {/* Info Message */}
          <div className="bg-blue-50 p-3 rounded-md flex gap-2">
            <FileText className="w-4 h-4 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium">Auto Progress Update</p>
              <p className="text-xs mt-1">
                Completing this subtask will automatically update the parent task's progress.
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
                Complete Subtask
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SubtaskCompleteDialog;