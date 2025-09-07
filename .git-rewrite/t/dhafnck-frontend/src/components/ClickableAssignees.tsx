import React from "react";
import { Badge } from "./ui/badge";
import { Task, Subtask } from "../api";

interface ClickableAssigneesProps {
  assignees: string[];
  task: Task | Subtask;
  onAgentClick: (agentName: string, task: Task | Subtask) => void;
  variant?: "default" | "secondary" | "destructive" | "outline";
  className?: string;
  showAsString?: boolean; // Option to show as comma-separated string instead of badges
}

export const ClickableAssignees: React.FC<ClickableAssigneesProps> = ({
  assignees,
  task,
  onAgentClick,
  variant = "secondary",
  className = "",
  showAsString = false
}) => {
  // Debug logging
  console.log('ClickableAssignees received:', {
    assignees,
    isArray: Array.isArray(assignees),
    length: assignees?.length,
    taskTitle: task.title,
    stringified: JSON.stringify(assignees)
  });

  // Clean up assignees data to handle any edge cases
  let cleanAssignees: string[] = [];
  
  if (Array.isArray(assignees)) {
    // Filter out any invalid entries like "[", "]", " ", etc.
    cleanAssignees = assignees.filter(assignee => {
      if (typeof assignee !== 'string') return false;
      const trimmed = assignee.trim();
      // Remove single bracket characters or empty strings
      return trimmed && trimmed !== '[' && trimmed !== ']' && trimmed !== '[]';
    });
  }

  if (!cleanAssignees || cleanAssignees.length === 0) {
    return <span className="text-sm text-muted-foreground">Unassigned</span>;
  }

  if (showAsString) {
    // Show as clickable text (for backward compatibility)
    return (
      <span className="text-sm font-medium">
        {cleanAssignees.map((assignee, index) => (
          <React.Fragment key={index}>
            <span
              className="cursor-pointer hover:text-primary underline decoration-dotted"
              onClick={() => onAgentClick(assignee, task)}
              title={`Click to call ${assignee}`}
            >
              {assignee}
            </span>
            {index < cleanAssignees.length - 1 && ", "}
          </React.Fragment>
        ))}
      </span>
    );
  }

  // Show as clickable badges
  return (
    <div className={`flex flex-wrap gap-1 ${className}`}>
      {cleanAssignees.map((assignee: string, index: number) => (
        <Badge
          key={index}
          variant={variant}
          className="px-2 cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
          onClick={() => onAgentClick(assignee, task)}
          title={`Click to call ${assignee}`}
        >
          {assignee}
        </Badge>
      ))}
    </div>
  );
};

export default ClickableAssignees;