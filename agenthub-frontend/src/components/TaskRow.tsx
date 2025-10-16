import { ChevronDown, ChevronRight, Eye, Pencil, Trash2, Users } from "lucide-react";
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Task } from "../api";
import { useTaskAnimation } from "../hooks/useTaskAnimation";
import logger from "../utils/logger";
import ClickableAssignees from "./ClickableAssignees";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { HolographicPriorityBadge, HolographicStatusBadge } from "./ui/holographic-badges";
import { ProgressDisplayEnhanced } from "./ui/ProgressDisplay";
import { TableCell, TableRow } from "./ui/table";

import LazySubtaskList from "./LazySubtaskList";
import "./TaskRow.animations.css";

// Lightweight task summary interface
interface TaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  subtask_count: number;
  assignees_count: number;
  assignees: string[];
  has_dependencies: boolean;
  dependency_count: number;
}

interface TaskRowProps {
  summary: TaskSummary;
  isExpanded: boolean;
  isLoading: boolean;
  fullTask: Task | null;
  isHighlighted: boolean;
  isHovered: boolean;
  projectId: string;
  taskTreeId: string;
  isMobile: boolean;
  isNew?: boolean; // Flag indicating this is a newly created task (should start hidden)

  // Animation event callbacks from parent (placeholders)
  onPlayCreateAnimation: () => void;
  onPlayDeleteAnimation: () => void;
  onPlayUpdateAnimation: () => void;

  // Other callbacks
  onToggleExpansion: () => void;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  onHover: (taskId: string | null) => void;

  // Callback registration function from parent
  onRegisterCallbacks?: (taskId: string, callbacks: {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }) => void;
  onUnregisterCallbacks?: (taskId: string) => void;
}

const TaskRow: React.FC<TaskRowProps> = ({
  summary,
  isExpanded,
  isLoading,
  fullTask,
  isHighlighted,
  isHovered,
  projectId,
  taskTreeId,
  isMobile,
  isNew = false,
  onPlayCreateAnimation,
  onPlayDeleteAnimation,
  onPlayUpdateAnimation,
  onToggleExpansion,
  onOpenDialog,
  onHover,
  onRegisterCallbacks,
  onUnregisterCallbacks
}) => {
  // 🔴 CRITICAL: Detect which mode is being used - only log when expanded or when state changes
  React.useEffect(() => {
    if (isExpanded) {
      console.log('[TaskRow] 📱 TASK EXPANDED:', {
        taskId: summary.id,
        taskTitle: summary.title,
        mode: isMobile ? 'MOBILE' : 'DESKTOP',
        isExpanded,
        hasFullTask: !!fullTask,
        fullTask: fullTask ? { id: fullTask.id, status: fullTask.status } : null,
        subtask_count: summary.subtask_count,
        timestamp: new Date().toISOString()
      });
    }
  }, [isExpanded, summary.id, summary.title, summary.subtask_count, isMobile, fullTask]);

  // Navigation hook for task detail URLs
  const navigate = useNavigate();

  // Use the animation hook
  const {
    animationState,
    isVisible,
    animationClass,
    mobileElementRef,
    desktopElementRef,
    playCreateAnimation,
    playDeleteAnimation,
    playUpdateAnimation
  } = useTaskAnimation(summary, isMobile);

  // Register animation callbacks with parent
  useEffect(() => {
    if (onRegisterCallbacks) {
      logger.debug('TaskRow registering callbacks for task', { component: 'TaskRow', taskId: summary.id });
      onRegisterCallbacks(summary.id, {
        playCreateAnimation: () => playCreateAnimation('websocket'),
        playDeleteAnimation: () => playDeleteAnimation('websocket'),
        playUpdateAnimation: () => playUpdateAnimation('websocket')
      });
    } else {
      logger.warn('TaskRow: No onRegisterCallbacks provided for task', { component: 'TaskRow', taskId: summary.id });
    }

    // Cleanup on unmount
    return () => {
      if (onUnregisterCallbacks) {
        logger.debug('TaskRow unregistering callbacks for task', { component: 'TaskRow', taskId: summary.id });
        onUnregisterCallbacks(summary.id);
      }
    };
  }, [summary.id, playCreateAnimation, playDeleteAnimation, playUpdateAnimation, onRegisterCallbacks, onUnregisterCallbacks]);

  // Note: WebSocket animations are now handled by the useTaskAnimation hook
  // through the AnimationFactory system which provides better coordination

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }

  // Animation classes - use CSS classes instead of inline styles
  const getAnimationClasses = () => {
    const baseClasses = 'transition-all duration-200';

    // Add .taskRowNew class for initial hidden state
    const newClass = (isNew && animationState === 'none') ? 'taskRowNew' : '';

    switch (animationState) {
      case 'creating':
        return `${baseClasses} taskRowCreateAnimation border-teal-500 bg-teal-100 dark:bg-teal-950 ${newClass}`;
      case 'deleting':
        return `${baseClasses} taskRowDeleteAnimation border-red-500 bg-red-100 dark:bg-red-950`;
      case 'updating':
        return `${baseClasses} task-updating-animation`;
      default:
        return baseClasses + (
          isHighlighted
            ? ' border-blue-400 bg-orange-100 dark:bg-blue-950 shadow-md'
            : isHovered
            ? ' border-violet-400 shadow-lg bg-violet-200 dark:bg-violet-950'
            : ' border-surface-border dark:border-gray-700'
        ) + ` ${newClass}`;
    }
  };

  if (isMobile) {
    // Mobile Card View
    return (
      <div
          ref={mobileElementRef}
          className={`rounded-lg mb-3 cursor-pointer ${getAnimationClasses()}`}
          onMouseEnter={() => onHover(summary.id)}
          onMouseLeave={() => onHover(null)}
        >
          {/* Inner content */}
          <div className={`bg-surface dark:bg-gray-800 rounded-lg shadow-sm border w-full h-full`}>
          <div className="p-4">
            {/* Task Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="font-medium text-base mb-2 pr-2">{summary.title}</h3>
                {/* Enhanced Progress Display with cleaned text and tooltips */}
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
                {/* Single line with no wrap, truncation for overflow */}
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <HolographicStatusBadge status={summary.status as any} size="xs" />
                    <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
                  </div>
                  <div className="flex items-center gap-1 min-w-0 overflow-hidden">
                    {summary.subtask_count > 0 && (
                      <Badge variant="outline" className="text-xs whitespace-nowrap flex-shrink-0">
                        {summary.subtask_count} subtasks
                      </Badge>
                    )}
                    {summary.has_dependencies && (
                      <Badge
                        variant="outline"
                        className="text-xs cursor-help whitespace-nowrap flex-shrink-0"
                        title={`This task depends on ${summary.dependency_count} other task${summary.dependency_count === 1 ? '' : 's'}.`}
                      >
                        {summary.dependency_count} {summary.dependency_count === 1 ? 'dep' : 'deps'}
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
                          className="text-xs"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  console.log('[TaskRow] 🖱️ MOBILE expand button clicked:', {
                    taskId: summary.id,
                    taskTitle: summary.title,
                    currentIsExpanded: isExpanded,
                    timestamp: new Date().toISOString()
                  });
                  e.stopPropagation();
                  onToggleExpansion();
                  console.log('[TaskRow] 🔄 MOBILE onToggleExpansion called');
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
            </div>

            {/* Action Buttons */}
            <div className="flex gap-1 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/dashboard/project/${projectId}/branch/${taskTreeId}/task/${summary.id}`);
                }}
                className="flex-1 min-w-[60px]"
              >
                <Eye className="w-3 h-3 mr-1" />
                View
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('edit', summary.id);
                }}
                className="flex-1 min-w-[60px]"
              >
                <Pencil className="w-3 h-3 mr-1" />
                Edit
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('assign', summary.id);
                }}
                className="flex-1 min-w-[60px]"
              >
                <Users className="w-3 h-3 mr-1" />
                Assign
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('delete', summary.id);
                }}
                title="Delete task"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>

          {/* Expanded Content - Only render LazySubtaskList if task has subtasks */}
          {(() => {
            const shouldRenderSubtasks = isExpanded && fullTask && summary.subtask_count > 0;
            console.log('[TaskRow] 🔍 MOBILE Subtask render decision:', {
              taskId: summary.id,
              taskTitle: summary.title,
              isExpanded,
              hasFullTask: !!fullTask,
              subtask_count: summary.subtask_count,
              shouldRenderSubtasks,
              timestamp: new Date().toISOString()
            });
            return shouldRenderSubtasks;
          })() && (
            <div className="border-t border-surface-border dark:border-gray-700">
              <div className="border-blue-400 dark:border-blue-600">
                <LazySubtaskList
                  projectId={projectId}
                  taskTreeId={taskTreeId}
                  parentTaskId={summary.id}
                />
              </div>
            </div>
          )}

          {/* Show message when expanded but no subtasks */}
          {isExpanded && fullTask && summary.subtask_count === 0 && (
            <div className="border-t border-surface-border dark:border-gray-700 p-4 text-center text-sm text-muted-foreground">
              No subtasks for this task - WORKING!
            </div>
          )}
          </div>
        </div>
    );
  } else {
    // Desktop Table View
    return (
      <>
        <TableRow
          ref={desktopElementRef}
          className={`cursor-pointer ${getAnimationClasses()}`}
          onMouseEnter={() => onHover(summary.id)}
          onMouseLeave={() => onHover(null)}
        >
          <TableCell className="w-[50px]">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                console.log('[TaskRow] 🖱️ DESKTOP expand button clicked:', {
                  taskId: summary.id,
                  taskTitle: summary.title,
                  currentIsExpanded: isExpanded,
                  timestamp: new Date().toISOString()
                });
                e.stopPropagation();
                onToggleExpansion();
                console.log('[TaskRow] 🔄 DESKTOP onToggleExpansion called');
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

          <TableCell className="">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span>{summary.title}</span>
                {summary.subtask_count > 0 && (
                  <Badge variant="outline" className="text-xs">
                    {summary.subtask_count}
                  </Badge>
                )}
              </div>
              {/* Enhanced Progress Display with cleaned text and tooltips */}
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

          <TableCell className="hidden sm:table-cell">
            <HolographicStatusBadge status={summary.status as any} size="sm" />
          </TableCell>

          <TableCell className="hidden md:table-cell">
            <HolographicPriorityBadge priority={summary.priority as any} size="sm" />
          </TableCell>

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

          <TableCell className="">
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/dashboard/project/${projectId}/branch/${taskTreeId}/task/${summary.id}`);
                }}
                title="View details"
                className="h-8 w-8"
              >
                <Eye className="w-4 h-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('assign', summary.id);
                }}
                title="Assign agents"
                className="h-8 w-8 hidden sm:inline-flex"
              >
                <Users className="w-4 h-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('edit', summary.id);
                }}
                title="Edit task"
                className="h-8 w-8"
              >
                <Pencil className="w-4 h-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('delete', summary.id);
                }}
                title="Delete task"
                className="h-8 w-8"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>

        {/* Only render LazySubtaskList if task has subtasks */}
        {(() => {
          const shouldRenderSubtasks = isExpanded && fullTask && summary.subtask_count > 0;
          console.log('[TaskRow] 🔍 DESKTOP Subtask render decision:', {
            taskId: summary.id,
            taskTitle: summary.title,
            isExpanded,
            hasFullTask: !!fullTask,
            subtask_count: summary.subtask_count,
            shouldRenderSubtasks,
            timestamp: new Date().toISOString()
          });
          return shouldRenderSubtasks;
        })() && (
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

        {/* Show message when expanded but no subtasks */}
        {isExpanded && fullTask && summary.subtask_count === 0 && (
          <TableRow className="theme-context-section">
            <TableCell colSpan={7} className="p-4 text-center text-sm text-muted-foreground">
              No subtasks for this task
            </TableCell>
          </TableRow>
        )}
      </>
    );
  }
};

export default TaskRow;