// SubtaskActions component - Action buttons for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import React from "react";
import { Plus } from "lucide-react";
import { Button } from "../../ui/button";

interface SubtaskActionsProps {
  onAddSubtask: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Action buttons component for the subtask list
 * Currently handles the "Add Subtask" action
 */
export function SubtaskActions({
  onAddSubtask,
  disabled = false,
  className = ""
}: SubtaskActionsProps) {

  return (
    <div className={`flex justify-end pt-2 border-t border-blue-200/50 dark:border-blue-800/50 ${className}`}>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled}
        className="mt-2 border-blue-300 text-blue-600 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-400 dark:hover:bg-blue-950/50 relative z-20"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onAddSubtask();
        }}
      >
        <Plus className="w-3 h-3 mr-1" />
        Add Subtask
      </Button>
    </div>
  );
}

export default SubtaskActions;