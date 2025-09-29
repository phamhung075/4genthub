import { ChevronDown, ChevronRight, Eye, Pencil, Trash2, Users } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Task } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ShimmerButton } from "./ui/shimmer-button";
import { HolographicPriorityBadge, HolographicStatusBadge } from "./ui/holographic-badges";
import { TableCell, TableRow } from "./ui/table";
import logger from "../utils/logger";
import { ProgressDisplayEnhanced } from "./ui/ProgressDisplay";
import { animationFactory, AnimationType } from "../services/AnimationFactory";

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
  created_at?: string; // Added for mount-time animation detection
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
  onToggleExpansion,
  onOpenDialog,
  onHover,
  onRegisterCallbacks,
  onUnregisterCallbacks
}) => {
  // CRITICAL DEBUG: Log TaskRow component mount
  console.log('🎬 [TaskRow] COMPONENT MOUNT/RENDER (using AnimationFactory):', {
    taskId: summary.id,
    taskTitle: summary.title,
    componentMounted: true,
    timestamp: new Date().toISOString(),
    hasCreatedAt: !!summary.created_at,
    createdAt: summary.created_at
  });

  // Navigation hook for task detail URLs
  const navigate = useNavigate();

  // Simplified state - visibility only (animations handled by factory)
  const [isVisible, setIsVisible] = useState(true);

  // Refs for DOM elements to register with AnimationFactory
  const mobileElementRef = useRef<HTMLDivElement>(null);
  const desktopElementRef = useRef<HTMLTableRowElement>(null);

  // Simplified animation handlers using centralized AnimationFactory
  const playCreateAnimation = useCallback((source: 'callback' | 'websocket' | 'mount' = 'callback') => {
    console.log('🎬 [TaskRow] playCreateAnimation called (delegating to AnimationFactory):', {
      taskId: summary.id,
      source
    });

    const success = animationFactory.animate(summary.id, 'create', source);

    logger.debug('TaskRow delegated create animation to factory', {
      component: 'TaskRow',
      taskId: summary.id,
      source,
      success
    });

    return success;
  }, [summary.id]);

  const playDeleteAnimation = useCallback((source: 'callback' | 'websocket' | 'mount' = 'callback') => {
    console.log('🎬 [TaskRow] playDeleteAnimation called (delegating to AnimationFactory):', {
      taskId: summary.id,
      source
    });

    const success = animationFactory.animate(summary.id, 'delete', source);

    logger.debug('TaskRow delegated delete animation to factory', {
      component: 'TaskRow',
      taskId: summary.id,
      source,
      success
    });

    // Handle visibility after delete animation
    if (success) {
      setTimeout(() => {
        logger.debug('TaskRow hiding after delete animation', { component: 'TaskRow', taskId: summary.id });
        setIsVisible(false);
      }, 1000); // 1s duration from AnimationFactory (enhanced)
    }

    return success;
  }, [summary.id]);

  const playUpdateAnimation = useCallback((source: 'callback' | 'websocket' | 'mount' = 'callback') => {
    console.log('🎬 [TaskRow] playUpdateAnimation called (delegating to AnimationFactory):', {
      taskId: summary.id,
      source
    });

    const success = animationFactory.animate(summary.id, 'update', source);

    logger.debug('TaskRow delegated update animation to factory', {
      component: 'TaskRow',
      taskId: summary.id,
      source,
      success
    });

    return success;
  }, [summary.id]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = isMobile ? mobileElementRef.current : desktopElementRef.current;

    if (currentElement) {
      console.log('🎬 [TaskRow] Registering element with AnimationFactory:', {
        taskId: summary.id,
        elementType: isMobile ? 'mobile' : 'desktop',
        element: currentElement.tagName
      });

      animationFactory.registerElement(summary.id, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          console.log('🎬 [TaskRow] Animation started:', { taskId: summary.id, type });
        },
        onAnimationEnd: (type: AnimationType) => {
          console.log('🎬 [TaskRow] Animation completed:', { taskId: summary.id, type });
        }
      });

      logger.debug('TaskRow registered with AnimationFactory', {
        component: 'TaskRow',
        taskId: summary.id,
        isMobile
      });
    } else {
      console.warn('🎬 [TaskRow] Failed to register - element ref not available:', {
        taskId: summary.id,
        isMobile,
        mobileRef: !!mobileElementRef.current,
        desktopRef: !!desktopElementRef.current
      });
    }

    // Cleanup on unmount
    return () => {
      console.log('🎬 [TaskRow] Unregistering from AnimationFactory:', summary.id);
      animationFactory.unregisterElement(summary.id);
      logger.debug('TaskRow unregistered from AnimationFactory', {
        component: 'TaskRow',
        taskId: summary.id
      });
    };
  }, [summary.id, isMobile]); // Re-register if mobile/desktop mode changes

  // Register animation callbacks with parent (simplified)
  useEffect(() => {
    if (onRegisterCallbacks) {
      logger.debug('TaskRow registering simplified callbacks for task', { component: 'TaskRow', taskId: summary.id });
      onRegisterCallbacks(summary.id, {
        playCreateAnimation: () => playCreateAnimation('callback'),
        playDeleteAnimation: () => playDeleteAnimation('callback'),
        playUpdateAnimation: () => playUpdateAnimation('callback')
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

  // Mount-time animation check for newly created tasks (simplified with AnimationFactory)
  useEffect(() => {
    // Check if this task was recently created and should trigger fade-in animation
    if (summary.created_at) {
      const createdTime = new Date(summary.created_at).getTime();
      const now = Date.now();
      const timeSinceCreated = now - createdTime;

      // If task was created within the last 10 seconds, trigger fade-in animation
      const isNewlyCreated = timeSinceCreated < 10000; // 10 seconds

      console.log('🎬 [TaskRow] MOUNT-TIME ANIMATION CHECK (AnimationFactory):', {
        taskId: summary.id,
        createdAt: summary.created_at,
        createdTime,
        currentTime: now,
        timeSinceCreated,
        isNewlyCreated,
        willTriggerAnimation: isNewlyCreated
      });

      if (isNewlyCreated) {
        // Add small delay to ensure DOM is ready and AnimationFactory registration is complete
        setTimeout(() => {
          console.log('🎬 [TaskRow] MOUNT-TIME ANIMATION TRIGGERED for newly created task:', summary.id);
          playCreateAnimation('mount');
        }, 100); // 100ms delay for DOM and registration readiness
      }
    }
  }, []); // Empty dependency array - only run on mount

  // REMOVED: Complex WebSocket event listeners - now handled by AnimationFactory
  // AnimationFactory receives WebSocket calls directly from WebSocketAnimationService
  // No need for CustomEvent coordination - factory handles everything centrally

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }


  // Simplified CSS classes - animations handled by AnimationFactory
  const getBaseClasses = () => {
    const baseClasses = 'transition-all duration-200';

    return baseClasses + (
      isHighlighted
        ? ' border-blue-400 bg-orange-100 dark:bg-blue-950 shadow-md'
        : isHovered
        ? ' border-violet-400 shadow-lg bg-violet-200 dark:bg-violet-950'
        : ' border-surface-border dark:border-gray-700'
    );
  };

  if (isMobile) {
    // Mobile Card View
    return (
      <>

        <div
          ref={mobileElementRef}
          className={`rounded-lg mb-3 cursor-pointer ${getBaseClasses()}`}
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
            </div>

            {/* Action Buttons */}
            <div className="flex gap-1 flex-wrap">
              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDialog('delete', summary.id);
                }}
                title="Delete task"
              >
                <Trash2 className="w-3 h-3" />
              </ShimmerButton>
            </div>
          </div>

          {/* Expanded Content - Only render LazySubtaskList if task has subtasks */}
          {isExpanded && fullTask && summary.subtask_count > 0 && (
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
              No subtasks for this task.
            </div>
          )}
          </div>
        </div>
      </>
    );
  } else {
    // Desktop Table View
    return (
      <>

        <TableRow
          ref={desktopElementRef}
          className={`cursor-pointer ${getBaseClasses()}`}
          onMouseEnter={() => onHover(summary.id)}
          onMouseLeave={() => onHover(null)}
        >
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
              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
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
              </ShimmerButton>

              <ShimmerButton
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
              </ShimmerButton>
            </div>
          </TableCell>
        </TableRow>

        {/* Only render LazySubtaskList if task has subtasks */}
        {isExpanded && fullTask && summary.subtask_count > 0 && (
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
              No subtasks for this task.
            </TableCell>
          </TableRow>
        )}
      </>
    );
  }
};

export default TaskRow;