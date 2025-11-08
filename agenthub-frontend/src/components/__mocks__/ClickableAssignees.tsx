import { vi } from 'vitest';
import React from 'react';

// Mock implementation of ClickableAssignees component
// Used in tests to avoid rendering complex Badge components and agent interactions

interface ClickableAssigneesProps {
  assignees: string[];
  task: any;
  onAgentClick: (agentName: string, task: any) => void;
  variant?: "default" | "secondary" | "destructive" | "outline";
  className?: string;
  showAsString?: boolean;
  compact?: boolean;
}

export const ClickableAssignees: React.FC<ClickableAssigneesProps> = ({
  assignees,
  task,
  onAgentClick,
  className = "",
  showAsString = false
}) => {
  if (showAsString) {
    return <span data-testid="clickable-assignees">{assignees.join(', ')}</span>;
  }

  return (
    <div data-testid="clickable-assignees" className={className}>
      {assignees.map((assignee, index) => (
        <button
          key={index}
          data-testid={`assignee-${assignee}`}
          onClick={() => onAgentClick(assignee, task)}
          aria-label={`View ${assignee} details`}
        >
          {assignee}
        </button>
      ))}
    </div>
  );
};

// Mock the module
vi.mock('../../components/ClickableAssignees', () => ({
  ClickableAssignees: vi.fn((props: ClickableAssigneesProps) => {
    if (props.showAsString) {
      return <span data-testid="clickable-assignees">{props.assignees.join(', ')}</span>;
    }
    return (
      <div data-testid="clickable-assignees" className={props.className}>
        {props.assignees.map((assignee, index) => (
          <button
            key={index}
            data-testid={`assignee-${assignee}`}
            onClick={() => props.onAgentClick(assignee, props.task)}
            aria-label={`View ${assignee} details`}
          >
            {assignee}
          </button>
        ))}
      </div>
    );
  })
}));

export default ClickableAssignees;
