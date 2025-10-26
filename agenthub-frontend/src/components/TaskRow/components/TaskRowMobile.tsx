import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { HolographicPriorityBadge, HolographicStatusBadge } from '../../ui/holographic-badges';
import { ProgressDisplayEnhanced } from '../../ui/ProgressDisplay';
import ClickableAssignees from '../../ClickableAssignees';
import LazySubtaskList from '../../LazySubtaskList';
import { TaskRowActions } from './TaskRowActions';
import { TaskCopyButtons } from './TaskCopyButtons';
import { TaskRowMobileProps } from '../../../types/taskTypes';
import { useTaskRowState } from '../hooks/useTaskRowState';

// CSS classes are now global (defined in src/styles/task-animations.css)

export const TaskRowMobile: React.FC<TaskRowMobileProps> = ({
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
  elementRef,
  animationClass = ''
}) => {
  const { getBaseClasses } = useTaskRowState();

  // Calculate counts from arrays (replaces removed backend count fields)
  const subtaskCount = fullTask?.subtasks?.length ?? 0;
  const dependencyCount = fullTask?.dependencies?.length ?? 0;

  // Combine animation classes with loading state
  const loadingClass = isLoading ? 'loading' : '';
  const containerClasses = `rounded-lg mb-3 cursor-pointer ${getBaseClasses(isHighlighted, isHovered)} ${animationClass} ${loadingClass}`.trim();

  return (
    <>
      <div
        ref={elementRef}
        className={containerClasses}
        onMouseEnter={() => onHover(summary.id)}
        onMouseLeave={() => onHover(null)}
      >
        <div className={`bg-surface dark:bg-gray-800 rounded-lg shadow-sm border w-full h-full`}>
          <div className="p-4">
            {/* Task Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-start gap-2 mb-2">
                  <TaskCopyButtons
                    taskId={summary.id}
                    taskName={summary.title}
                    size="sm"
                    className="flex-shrink-0 mt-0.5"
                  />
                  <h3 className="font-medium text-base pr-2">{summary.title}</h3>
                </div>

                {/* Progress Display */}
                <div className="mb-2">
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
                    maxTextLength={80}
                  />
                </div>

                {/* Badges and info */}
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <HolographicStatusBadge status={summary.status as any} size="xs" />
                    <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
                  </div>
                  <div className="flex items-center gap-1 min-w-0 overflow-hidden">
                    {subtaskCount > 0 && (
                      <Badge variant="outline" className="text-xs whitespace-nowrap flex-shrink-0">
                        {subtaskCount} subtasks
                      </Badge>
                    )}
                    {summary.has_dependencies && (
                      <Badge
                        variant="outline"
                        className="text-xs cursor-help whitespace-nowrap flex-shrink-0"
                        title={`This task depends on ${dependencyCount} other task${dependencyCount === 1 ? '' : 's'}.`}
                      >
                        {dependencyCount} {dependencyCount === 1 ? 'dep' : 'deps'}
                      </Badge>
                    )}
                    {summary.assignees && summary.assignees.length > 0 && (
                      <div className="min-w-0 overflow-hidden">
                        <ClickableAssignees
                          assignees={summary.assignees}
                          task={fullTask || summary as any}
                          onAgentClick={(agentName, task) => {
                            onOpenDialog('agent-info', undefined, { agentName, taskTitle: task.title });
                          }}
                          variant="secondary"
                          className=""
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Expand button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleExpansion();
                }}
                disabled={isLoading}
                className="flex-shrink-0"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                ) : isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </Button>
            </div>

            {/* Actions */}
            <div className="flex justify-end mt-3 pt-3 border-t border-surface-border dark:border-gray-700">
              <TaskRowActions
                taskId={summary.id}
                projectId={projectId}
                taskTreeId={taskTreeId}
                onOpenDialog={onOpenDialog}
                variant="mobile"
              />
            </div>
          </div>

          {/* Always show LazySubtaskList when expanded */}
          {isExpanded && fullTask && (
            <div className="border-t border-surface-border dark:border-gray-700 p-4">
              <LazySubtaskList
                projectId={projectId}
                taskTreeId={taskTreeId}
                parentTaskId={summary.id}
              />
            </div>
          )}
        </div>
      </div>
    </>
  );
};