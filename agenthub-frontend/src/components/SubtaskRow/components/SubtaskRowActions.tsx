// SubtaskRowActions - Action buttons component
// Single responsibility: Handle subtask action buttons

import React from 'react';
import { Check, Eye, Pencil, Trash2 } from "lucide-react";
import { Button } from "../../ui/button";
import type { SubtaskRowActionsProps } from '../../../types/subtaskTypes';

export const SubtaskRowActions: React.FC<SubtaskRowActionsProps> = ({
  subtaskId,
  onView,
  onEdit,
  onComplete,
  onDelete
}) => {
  return (
    <div className="flex gap-1">
      <Button
        size="icon"
        variant="ghost"
        onClick={onView}
        className="h-8 w-8 hover:bg-cyan-500/10"
        title="View details"
      >
        <Eye className="h-4 w-4 text-cyan-400" />
      </Button>

      <Button
        size="icon"
        variant="ghost"
        onClick={onEdit}
        className="h-8 w-8 hover:bg-blue-500/10"
        title="Edit subtask"
      >
        <Pencil className="h-4 w-4 text-blue-400" />
      </Button>

      <Button
        size="icon"
        variant="ghost"
        onClick={onComplete}
        className="h-8 w-8 hover:bg-green-500/10"
        title="Complete subtask"
      >
        <Check className="h-4 w-4 text-green-400" />
      </Button>

      <Button
        size="icon"
        variant="ghost"
        onClick={onDelete}
        className="h-8 w-8 hover:bg-red-500/10"
        title="Delete subtask"
      >
        <Trash2 className="h-4 w-4 text-red-400" />
      </Button>
    </div>
  );
};