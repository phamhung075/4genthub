import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { HolographicPriorityBadge, HolographicStatusBadge } from '../../ui/holographic-badges';
import { TableCell, TableRow } from '../../ui/table';
import { ProgressDisplayEnhanced } from '../../ui/ProgressDisplay';
import ClickableAssignees from '../../ClickableAssignees';
import LazySubtaskList from '../../LazySubtaskList';
import { TaskRowActions } from './TaskRowActions';
import { TaskCopyButtons } from './TaskCopyButtons';
import { TaskRowDesktopProps } from '../../../types/taskTypes';
import { useTaskRowState } from '../hooks/useTaskRowState';

export const TaskRowDesktop: React.FC<TaskRowDesktopProps> = ({
  summary,
  fullTask,
  isHighlighted,
  isHovered,
  isExpanded,
  isLoading,
  projectId,
  taskTreeId,
  onToggleExpansion,
  onOpenDialog,
  onHover,
  elementRef
}) => {
  const { getBaseClasses } = useTaskRowState();

  return (
    <>
      <TableRow
        ref={elementRef}
        className={`cursor-pointer ${getBaseClasses(isHighlighted, isHovered)}`}
        onMouseEnter={() => onHover(summary.id)}
        onMouseLeave={() => onHover(null)}
      >
        {/* Expand/Collapse Button */}
        <TableCell className="w-[50px]">
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpansion();
            }}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
            ) : isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </Button>
        </TableCell>

        {/* Title and Progress */}
        <TableCell className="">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <TaskCopyButtons
                taskId={summary.id}
                taskName={summary.title}
                size="sm"
              />
              <span>{summary.title}</span>
              {summary.subtask_count > 0 && (
                <Badge variant="outline" className="text-xs">
                  {summary.subtask_count}
                </Badge>
              )}
            </div>
            <ProgressDisplayEnhanced
              status={fullTask?.status || summary.status}
              progressPercentage={fullTask?.progress_percentage}
              progressState={fullTask?.progress_state}
              progressHistory={fullTask?.progress_history}
              size="sm"
              variant="compact"
              showLabels={false}
              animate={true}
              compactLayout={true}
              maxTextLength={60}
            />
          </div>
        </TableCell>

        {/* Status */}
        <TableCell className="hidden sm:table-cell">
          <HolographicStatusBadge status={summary.status as any} size="sm" />
        </TableCell>

        {/* Priority */}
        <TableCell className="hidden md:table-cell">
          <HolographicPriorityBadge priority={summary.priority as any} size="sm" />
        </TableCell>

        {/* Dependencies */}
        <TableCell className="hidden lg:table-cell">
          {summary.has_dependencies ? (
            <Badge
              variant="outline"
              className="text-xs cursor-help"
              title={`This task depends on ${summary.dependency_count} other task${summary.dependency_count === 1 ? '' : 's'}.`}
            >
              {summary.dependency_count} {summary.dependency_count === 1 ? 'dependency' : 'dependencies'}
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground">None</span>
          )}
        </TableCell>

        {/* Assignees */}
        <TableCell className="hidden md:table-cell max-w-[200px] p-2 align-top">
          {summary.assignees && summary.assignees.length > 0 ? (
            <ClickableAssignees
              assignees={summary.assignees}
              task={fullTask || summary as any}
              onAgentClick={(agentName, task) => {
                onOpenDialog('agent-info', undefined, { agentName, taskTitle: task.title });
              }}
              variant="secondary"
              className=""
              compact={true}
            />
          ) : (
            <span className="text-xs text-muted-foreground">Unassigned</span>
          )}
        </TableCell>

        {/* Actions */}
        <TableCell className="">
          <TaskRowActions
            taskId={summary.id}
            projectId={projectId}
            taskTreeId={taskTreeId}
            onOpenDialog={onOpenDialog}
            variant="desktop"
          />
        </TableCell>
      </TableRow>

      {/* Always show LazySubtaskList when expanded */}
      {isExpanded && fullTask && (
        <TableRow className="theme-context-section">
          <TableCell colSpan={7} className="p-0">
            <div className="border-blue-400 dark:border-blue-600 ml-8">
              <LazySubtaskList
                projectId={projectId}
                taskTreeId={taskTreeId}
                parentTaskId={summary.id}
              />
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
};