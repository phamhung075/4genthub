// SubtaskRowAssignees - Display assignee information
// Single responsibility: Render assignee badges

import React from 'react';
import { Badge } from "../../ui/badge";
import type { SubtaskRowAssigneesProps } from '../../../types/subtaskTypes';

export const SubtaskRowAssignees: React.FC<SubtaskRowAssigneesProps> = ({
  assignees = [],
  assigneesCount,
  onAgentInfoClick
}) => {
  if (assigneesCount === 0) {
    return (
      <Badge variant="outline" className="text-xs">
        No assignees
      </Badge>
    );
  }

  return (
    <div className="flex flex-wrap gap-1">
      {assignees.slice(0, 2).map(assignee => (
        <Badge
          key={assignee}
          variant="secondary"
          className="text-xs cursor-pointer hover:bg-primary/20"
          onClick={() => onAgentInfoClick(assignee)}
        >
          {assignee}
        </Badge>
      ))}

      {assigneesCount > 2 && (
        <Badge variant="outline" className="text-xs">
          +{assigneesCount - 2}
        </Badge>
      )}
    </div>
  );
};