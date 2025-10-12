import React from 'react';
import { Table, TableBody, TableHead, TableHeader, TableRow } from "../../ui/table";
import TaskRow from "../../TaskRow/TaskRowRefactored";
import { TaskSummary } from "../../../types/taskTypes";

interface TaskListContentProps {
  displayTasks: TaskSummary[];
  isMobile: boolean;
  expandedTasks: Set<string>;
  loadingTasks: Set<string>;
  fullTasks: Map<string, any>;
  highlightedDependencies: Set<string>;
  hoveredTaskId: string | null;
  projectId: string;
  taskTreeId: string;
  onToggleExpand: (taskId: string) => void;
  onOpenDialog: (type: string, taskId?: string, data?: any) => void;
  onHoverTask: (taskId: string | null) => void;
  onHighlightDependencies: (dependencies: Set<string>) => void;
}

export const TaskListContent: React.FC<TaskListContentProps> = ({
  displayTasks,
  isMobile,
  expandedTasks,
  loadingTasks,
  fullTasks,
  highlightedDependencies,
  hoveredTaskId,
  projectId,
  taskTreeId,
  onToggleExpand,
  onOpenDialog,
  onHoverTask,
  onHighlightDependencies
}) => {
  const renderTaskRow = (summary: TaskSummary, isMobileView: boolean) => {
    return (
      <TaskRow
        key={summary.id}
        summary={summary}
        isExpanded={expandedTasks.has(summary.id)}
        isLoading={loadingTasks.has(summary.id)}
        fullTask={fullTasks.get(summary.id) || null}
        isHighlighted={highlightedDependencies.has(summary.id)}
        isHovered={hoveredTaskId === summary.id}
        projectId={projectId}
        taskTreeId={taskTreeId}
        isMobile={isMobileView}
        onToggleExpansion={() => onToggleExpand(summary.id)}
        onOpenDialog={onOpenDialog}
        onHover={onHoverTask}
      />
    );
  };

  if (isMobile) {
    // Mobile Card View
    return (
      <div className="space-y-2">
        {displayTasks.map(task => renderTaskRow(task, true))}
      </div>
    );
  }

  // Desktop Table View
  return (
    <div className="mt-3 overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]"></TableHead>
            <TableHead>Title</TableHead>
            <TableHead className="hidden sm:table-cell">Status</TableHead>
            <TableHead className="hidden md:table-cell">Priority</TableHead>
            <TableHead className="hidden lg:table-cell">Dependencies</TableHead>
            <TableHead className="hidden md:table-cell">Assignees</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayTasks.map(task => renderTaskRow(task, false))}
        </TableBody>
      </Table>
    </div>
  );
};