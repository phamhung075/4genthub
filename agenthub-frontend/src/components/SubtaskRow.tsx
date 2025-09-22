import { Check, Eye, Pencil, Trash2 } from "lucide-react";
import React, { useState, useCallback, useEffect } from "react";
import { Subtask } from "../api";
import { SubtaskSummary } from "../api-lazy";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { TableCell, TableRow } from "./ui/table";
import { CopyableId } from "./ui/CopyableId";
import { ParentTaskReference } from "./ui/ParentTaskReference";
import logger from "../utils/logger";
import styles from "./SubtaskRow.module.css";

// Using SubtaskSummary interface from api-lazy.ts

interface SubtaskRowProps {
  summary: SubtaskSummary;
  fullSubtask: Subtask | null;
  isLoading: boolean;
  showDetails: boolean;
  parentTaskId: string; // Add parent task ID for context display

  // Animation event callbacks from parent (placeholders)
  onPlayCreateAnimation: () => void;
  onPlayDeleteAnimation: () => void;
  onPlayUpdateAnimation: () => void;

  // Other callbacks
  onSubtaskAction: (action: 'details' | 'edit' | 'complete', subtaskId: string) => void;
  onAgentInfoClick: (agentName: string) => void;
  onDeleteSubtask: (subtaskId: string) => void;

  // Callback registration function from parent
  onRegisterCallbacks?: (subtaskId: string, callbacks: {
    playCreateAnimation: () => void;
    playDeleteAnimation: () => void;
    playUpdateAnimation: () => void;
  }) => void;
  onUnregisterCallbacks?: (subtaskId: string) => void;
}

const SubtaskRow: React.FC<SubtaskRowProps> = ({
  summary,
  fullSubtask,
  isLoading,
  showDetails,
  parentTaskId,
  onPlayCreateAnimation,
  onPlayDeleteAnimation,
  onPlayUpdateAnimation,
  onSubtaskAction,
  onAgentInfoClick,
  onDeleteSubtask,
  onRegisterCallbacks,
  onUnregisterCallbacks
}) => {
  // Handler for view details - use dialog instead of navigation
  const handleViewDetails = useCallback(() => {
    onSubtaskAction('details', summary.id);
  }, [onSubtaskAction, summary.id]);

  // Internal animation state
  const [animationState, setAnimationState] = useState<'none' | 'creating' | 'deleting' | 'updating'>('none');
  const [isVisible, setIsVisible] = useState(true);

  // Animation handlers
  const playCreateAnimation = useCallback(() => {
    setAnimationState('creating');
    setTimeout(() => setAnimationState('none'), 800); // Clear after animation (longer)
  }, []);

  const playDeleteAnimation = useCallback(() => {
    logger.debug('🎬 SubtaskRow starting delete animation for:', summary.id);
    setAnimationState('deleting');
    // After animation completes, hide the row
    setTimeout(() => {
      logger.debug('🎬 SubtaskRow delete animation complete, hiding:', summary.id);
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
      logger.debug('📝 SubtaskRow registering callbacks for subtask:', summary.id);
      onRegisterCallbacks(summary.id, {
        playCreateAnimation,
        playDeleteAnimation,
        playUpdateAnimation
      });
    } else {
      logger.warn('⚠️ SubtaskRow: No onRegisterCallbacks provided for subtask:', summary.id);
    }

    // Cleanup on unmount
    return () => {
      if (onUnregisterCallbacks) {
        logger.debug('🧹 SubtaskRow unregistering callbacks for subtask:', summary.id);
        onUnregisterCallbacks(summary.id);
      }
    };
  }, [summary.id, playCreateAnimation, playDeleteAnimation, playUpdateAnimation, onRegisterCallbacks, onUnregisterCallbacks]);

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }

  // Animation classes
  const getAnimationClasses = () => {
    const baseClasses = 'transition-all duration-200';

    switch (animationState) {
      case 'creating':
        return `${baseClasses} border-green-500 bg-green-100 dark:bg-green-950`;
      case 'deleting':
        return `${baseClasses} border-red-500 bg-red-100 dark:bg-red-950`;
      case 'updating':
        return `${baseClasses} ${styles.subtaskUpdatingAnimation}`;
      default:
        return `${baseClasses} hover:bg-gray-50 dark:hover:bg-gray-800/20`;
    }
  };

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

  return (
    <React.Fragment>
      <TableRow
        className={`text-sm ${getAnimationClasses()}`}
        style={getAnimationStyle()}
      >
        <TableCell className="pl-8">
          <div className="space-y-1">
            {/* Main title row with indicator */}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-400 dark:bg-blue-600"></div>
              <span className="text-gray-700 dark:text-gray-300 font-medium">{summary.title}</span>
              {summary.progress_percentage !== undefined && (
                <Badge variant="outline" className="text-xs bg-gray-100 dark:bg-gray-800/50 border-gray-300 dark:border-gray-700">
                  {summary.status === 'done' ? 100 : summary.progress_percentage}%
                </Badge>
              )}
            </div>

            {/* Subtask ID and Parent Task Reference */}
            <div className="flex items-center gap-3 ml-4">
              <CopyableId
                id={summary.id}
                label="ID:"
                variant="inline"
                size="xs"
                abbreviated={true}
                showCopyButton={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <ParentTaskReference
                parentTaskId={parentTaskId}
                variant="inline"
                showId={false}
                className="text-gray-500 dark:text-gray-400"
              />
            </div>
          </div>
        </TableCell>

        <TableCell>
          <HolographicStatusBadge status={summary.status as any} size="xs" />
        </TableCell>

        <TableCell>
          <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
        </TableCell>

        <TableCell>
          {summary.assignees && summary.assignees.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {summary.assignees.map((assignee, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    onAgentInfoClick(assignee);
                  }}
                  title={`View ${assignee} information`}
                >
                  {assignee}
                </Badge>
              ))}
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">Unassigned</span>
          )}
        </TableCell>

        <TableCell>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleViewDetails();
              }}
              disabled={isLoading}
              title="View details"
            >
              {isLoading ? (
                <div className="w-3 h-3 border border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              ) : (
                <Eye className="w-3 h-3" />
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSubtaskAction('edit', summary.id);
              }}
              disabled={isLoading || summary.status === 'done'}
              title="Edit"
            >
              <Pencil className="w-3 h-3" />
            </Button>

            {summary.status !== 'done' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onSubtaskAction('complete', summary.id);
                }}
                disabled={isLoading}
                title="Complete"
              >
                <Check className="w-3 h-3" />
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSubtask(summary.id);
              }}
              title="Delete subtask"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        </TableCell>
      </TableRow>

      {/* Subtask Details Row */}
      {showDetails && fullSubtask && (
        <TableRow className="bg-blue-50/30 dark:bg-blue-950/10">
          <TableCell colSpan={5} className="pl-12">
            <div className="py-2 space-y-2">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                <strong>Description:</strong> {fullSubtask.description || 'No description'}
              </div>
              {fullSubtask.assignees && fullSubtask.assignees.length > 0 && (
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  <strong>Assignees:</strong> {fullSubtask.assignees.join(', ')}
                </div>
              )}
              {fullSubtask.progress_notes && (
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  <strong>Progress Notes:</strong> {fullSubtask.progress_notes}
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </React.Fragment>
  );
};

export default SubtaskRow;