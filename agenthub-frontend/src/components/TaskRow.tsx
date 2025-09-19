import { ChevronDown, ChevronRight, Eye, FileText, Pencil, Trash2, Users } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import { Task } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { HolographicPriorityBadge, HolographicStatusBadge } from "./ui/holographic-badges";
import { TableCell, TableRow } from "./ui/table";

import LazySubtaskList from "./LazySubtaskList";

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
  has_context: boolean;
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
  onPlayCreateAnimation,
  onPlayDeleteAnimation,
  onPlayUpdateAnimation,
  onToggleExpansion,
  onOpenDialog,
  onHover,
  onRegisterCallbacks,
  onUnregisterCallbacks
}) => {
  // Internal animation state
  const [animationState, setAnimationState] = useState<'none' | 'creating' | 'deleting' | 'updating'>('none');
  const [isVisible, setIsVisible] = useState(true);

  // Animation handlers
  const playCreateAnimation = useCallback(() => {
    setAnimationState('creating');
    setTimeout(() => setAnimationState('none'), 800); // Clear after animation (longer)
  }, []);

  const playDeleteAnimation = useCallback(() => {
    console.log('🎬 TaskRow starting delete animation for:', summary.id);
    setAnimationState('deleting');
    // After animation completes, hide the row
    setTimeout(() => {
      console.log('🎬 TaskRow delete animation complete, hiding:', summary.id);
      setIsVisible(false);
    }, 800); // Animation duration (longer)
  }, [summary.id]);

  const playUpdateAnimation = useCallback(() => {
    setAnimationState('updating');
    setTimeout(() => setAnimationState('none'), 5000); // Clear after 5 seconds as requested
  }, []);

  // Register animation callbacks with parent
  useEffect(() => {
    if (onRegisterCallbacks) {
      console.log('📝 TaskRow registering callbacks for task:', summary.id);
      onRegisterCallbacks(summary.id, {
        playCreateAnimation,
        playDeleteAnimation,
        playUpdateAnimation
      });
    } else {
      console.warn('⚠️ TaskRow: No onRegisterCallbacks provided for task:', summary.id);
    }

    // Cleanup on unmount
    return () => {
      if (onUnregisterCallbacks) {
        console.log('🧹 TaskRow unregistering callbacks for task:', summary.id);
        onUnregisterCallbacks(summary.id);
      }
    };
  }, [summary.id, playCreateAnimation, playDeleteAnimation, playUpdateAnimation, onRegisterCallbacks, onUnregisterCallbacks]);

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }

  // Animation styles
  const getAnimationStyle = () => {
    switch (animationState) {
      case 'creating':
        return {
          animation: 'slideInFromRight 0.8s ease-out forwards'
        };
      case 'deleting':
        return {
          animation: 'slideOutToRight 0.8s ease-in forwards'
        };
      case 'updating':
        return {
          animation: 'shimmerBackground 2s linear infinite'
        };
      default:
        return {};
    }
  };

  // Animation classes
  const getAnimationClasses = () => {
    const baseClasses = 'transition-all duration-200';

    switch (animationState) {
      case 'creating':
        return `${baseClasses} border-green-500 bg-green-100 dark:bg-green-950`;
      case 'deleting':
        return `${baseClasses} border-red-500 bg-red-100 dark:bg-red-950`;
      case 'updating':
        return `${baseClasses} task-updating-animation`;
      default:
        return baseClasses + (
          isHighlighted
            ? ' border-blue-400 bg-orange-100 dark:bg-blue-950 shadow-md'
            : isHovered
            ? ' border-violet-400 shadow-lg bg-violet-200 dark:bg-violet-950'
            : ' border-surface-border dark:border-gray-700'
        );
    }
  };

  if (isMobile) {
    // Mobile Card View
    return (
      <>
        {/* Animation CSS */}
        <style>{`
          @keyframes slideInFromRight {
            0% {
              transform: translateX(100%);
              opacity: 0;
            }
            30% {
              transform: translateX(20%);
              opacity: 0.7;
            }
            70% {
              transform: translateX(-5%);
              opacity: 1;
            }
            100% {
              transform: translateX(0);
              opacity: 1;
            }
          }
          @keyframes slideOutToRight {
            0% {
              transform: translateX(0);
              opacity: 1;
              height: auto;
            }
            30% {
              transform: translateX(20%);
              opacity: 0.8;
            }
            80% {
              transform: translateX(100%);
              opacity: 0;
              height: auto;
            }
            100% {
              transform: translateX(100%);
              opacity: 0;
              height: 0;
              margin: 0;
              padding: 0;
              border: 0;
              overflow: hidden;
            }
          }
          @keyframes shimmerBackground {
            0% {
              background-position: 100% 50%;
            }
            100% {
              background-position: -100% 50%;
            }
          }

          .task-updating-animation {
            background: linear-gradient(90deg,
              transparent 0%,
              transparent 30%,
              rgba(59, 130, 246, 0.3) 40%,
              rgba(96, 165, 250, 0.3) 50%,
              rgba(147, 197, 253, 0.3) 60%,
              transparent 70%,
              transparent 100%);
            background-size: 200% 100%;
            animation: shimmerBackground 2s linear infinite;
          }
        `}</style>

        <div
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
                <div className="flex flex-wrap gap-2">
                  <HolographicStatusBadge status={summary.status as any} size="xs" />
                  <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
                  {summary.subtask_count > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {summary.subtask_count} subtasks
                    </Badge>
                  )}
                  {summary.has_dependencies && (
                    <Badge
                      variant="outline"
                      className="text-xs cursor-help"
                      title={`This task depends on ${summary.dependency_count} other task${summary.dependency_count === 1 ? '' : 's'}.`}
                    >
                      {summary.dependency_count} {summary.dependency_count === 1 ? 'dep' : 'deps'}
                    </Badge>
                  )}
                  {summary.assignees && summary.assignees.length > 0 && (
                    <ClickableAssignees
                      assignees={summary.assignees}
                      task={fullTask || summary as any}
                      onAgentClick={(agentName, task) => {
                        onOpenDialog('agent-info', undefined, { agentName, taskTitle: task.title });
                      }}
                      variant="secondary"
                      className="text-xs"
                    />
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onToggleExpansion}
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
                onClick={() => onOpenDialog('details', summary.id)}
                className="flex-1 min-w-[60px]"
              >
                <Eye className="w-3 h-3 mr-1" />
                View
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenDialog('edit', summary.id)}
                className="flex-1 min-w-[60px]"
              >
                <Pencil className="w-3 h-3 mr-1" />
                Edit
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenDialog('assign', summary.id)}
                className="flex-1 min-w-[60px]"
              >
                <Users className="w-3 h-3 mr-1" />
                Assign
              </Button>

              {summary.has_context && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenDialog('context', summary.id)}
                  title="View context"
                >
                  <FileText className="w-3 h-3" />
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenDialog('delete', summary.id)}
                title="Delete task"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>

          {/* Expanded Content - Always render but control visibility */}
          <div style={{ display: isExpanded && fullTask ? 'block' : 'none' }}>
            <div className="border-t border-surface-border dark:border-gray-700">
              <div className="border-blue-400 dark:border-blue-600">
                <LazySubtaskList
                  projectId={projectId}
                  taskTreeId={taskTreeId}
                  parentTaskId={summary.id}
                />
              </div>
            </div>
          </div>
          </div>
        </div>
      </>
    );
  } else {
    // Desktop Table View
    return (
      <>
        {/* Animation CSS */}
        <style>{`
          @keyframes slideInFromRight {
            0% {
              transform: translateX(100%);
              opacity: 0;
            }
            30% {
              transform: translateX(20%);
              opacity: 0.7;
            }
            70% {
              transform: translateX(-5%);
              opacity: 1;
            }
            100% {
              transform: translateX(0);
              opacity: 1;
            }
          }
          @keyframes slideOutToRight {
            0% {
              transform: translateX(0);
              opacity: 1;
              height: auto;
            }
            30% {
              transform: translateX(20%);
              opacity: 0.8;
            }
            80% {
              transform: translateX(100%);
              opacity: 0;
              height: auto;
            }
            100% {
              transform: translateX(100%);
              opacity: 0;
              height: 0;
              margin: 0;
              padding: 0;
              border: 0;
              overflow: hidden;
            }
          }
          @keyframes shimmerBackground {
            0% {
              background-position: 100% 50%;
            }
            100% {
              background-position: -100% 50%;
            }
          }

          .task-updating-animation {
            background: linear-gradient(90deg,
              transparent 0%,
              transparent 30%,
              rgba(59, 130, 246, 0.3) 40%,
              rgba(96, 165, 250, 0.3) 50%,
              rgba(147, 197, 253, 0.3) 60%,
              transparent 70%,
              transparent 100%);
            background-size: 200% 100%;
            animation: shimmerBackground 2s linear infinite;
          }
        `}</style>

        <TableRow
          className={`cursor-pointer ${getAnimationClasses()}`}
          style={getAnimationStyle()}
          onMouseEnter={() => onHover(summary.id)}
          onMouseLeave={() => onHover(null)}
        >
          <TableCell className="w-[50px]">
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleExpansion}
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
            <div className="flex items-center gap-2">
              <span>{summary.title}</span>
              {summary.subtask_count > 0 && (
                <Badge variant="outline" className="text-xs">
                  {summary.subtask_count}
                </Badge>
              )}
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
                onClick={() => onOpenDialog('details', summary.id)}
                title="View details"
                className="h-8 w-8"
              >
                <Eye className="w-4 h-4" />
              </Button>

              {summary.has_context && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onOpenDialog('context', summary.id)}
                  title="View context"
                  className="h-8 w-8 hidden sm:inline-flex"
                >
                  <FileText className="w-4 h-4" />
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={() => onOpenDialog('assign', summary.id)}
                title="Assign agents"
                className="h-8 w-8 hidden sm:inline-flex"
              >
                <Users className="w-4 h-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => onOpenDialog('edit', summary.id)}
                title="Edit task"
                className="h-8 w-8"
              >
                <Pencil className="w-4 h-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => onOpenDialog('delete', summary.id)}
                title="Delete task"
                className="h-8 w-8"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>

        {/* Always render but control visibility */}
        <TableRow className="theme-context-section" style={{ display: isExpanded && fullTask ? 'table-row' : 'none' }}>
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
      </>
    );
  }
};

export default TaskRow;