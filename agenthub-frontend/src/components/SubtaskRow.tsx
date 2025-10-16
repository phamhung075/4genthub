import { Check, Copy, Eye, Pencil, Trash2, FileText } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import { Subtask } from "../api";
import { SubtaskSummary } from "../api-lazy";
import { useSubtaskAnimation } from "../hooks/useSubtaskAnimation";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { TableCell, TableRow } from "./ui/table";
import logger from "../utils/logger";
import styles from "./SubtaskRow.module.css";
import "../styles/subtask-animations.css";

// Using SubtaskSummary interface from api-lazy.ts

interface SubtaskRowProps {
  summary: SubtaskSummary;
  fullSubtask: Subtask | null;
  isLoading: boolean;
  showDetails: boolean;
  parentTaskId: string; // Add parent task ID for context display
  isNew?: boolean; // Flag indicating this is a newly created subtask (should start hidden)

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
  isNew = false,
  onPlayCreateAnimation,
  onPlayDeleteAnimation,
  onPlayUpdateAnimation,
  onSubtaskAction,
  onAgentInfoClick,
  onDeleteSubtask,
  onRegisterCallbacks,
  onUnregisterCallbacks
}) => {
  // Copy state management
  const [copiedId, setCopiedId] = useState(false);
  const [copiedName, setCopiedName] = useState(false);

  // Handler for view details - use dialog instead of navigation
  const handleViewDetails = useCallback(() => {
    onSubtaskAction('details', summary.id);
  }, [onSubtaskAction, summary.id]);

  // Copy to clipboard handlers
  const copyIdToClipboard = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(summary.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    } catch (err) {
      logger.error('Failed to copy subtask ID', { component: 'SubtaskRow', error: err });
    }
  }, [summary.id]);

  const copyNameToClipboard = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(summary.title);
      setCopiedName(true);
      setTimeout(() => setCopiedName(false), 2000);
    } catch (err) {
      logger.error('Failed to copy subtask name', { component: 'SubtaskRow', error: err });
    }
  }, [summary.title]);

  // Use the animation hook
  const {
    animationState,
    isVisible,
    animationClass,
    elementRef
  } = useSubtaskAnimation({
    subtaskId: summary.id,
    onRegisterCallbacks,
    onUnregisterCallbacks
  });

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }

  // Animation classes - use CSS classes instead of inline styles
  const getAnimationClasses = () => {
    const baseClasses = 'transition-all duration-200';

    // Add .subtaskRowNew class for initial hidden state
    const newClass = (isNew && animationState === 'none') ? 'subtaskRowNew' : '';

    switch (animationState) {
      case 'creating':
        return `${baseClasses} subtaskRowCreateAnimation border-green-500 bg-green-100 dark:bg-green-950 ${newClass}`;
      case 'deleting':
        return `${baseClasses} subtaskRowDeleteAnimation border-red-500 bg-red-100 dark:bg-red-950`;
      case 'updating':
        return `${baseClasses} ${styles.subtaskUpdatingAnimation}`;
      default:
        return `${baseClasses} hover:bg-gray-50 dark:hover:bg-gray-800/20 ${newClass}`;
    }
  };

  // Debug log to verify component renders
  useEffect(() => {
    console.log('🔧 [SubtaskRow] Rendering with copy buttons:', {
      subtaskId: summary.id,
      subtaskTitle: summary.title,
      hasCopyButtons: true
    });
  }, [summary.id, summary.title]);

  return (
    <React.Fragment>
      <TableRow
        ref={elementRef}
        className={`text-sm ${getAnimationClasses()}`}
      >
        {/* Empty cell to align with parent's expand button column */}
        <TableCell className="w-[50px]"></TableCell>

        {/* Title column - wider to match parent task title column */}
        <TableCell className="">
          <div className="flex items-center gap-2 pl-4">
            {/* Copy buttons before title */}
            <Button
              variant="ghost"
              size="icon"
              onClick={copyIdToClipboard}
              title={copiedId ? "ID Copied!" : "Copy ID"}
              className="h-6 w-6 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950 flex-shrink-0"
            >
              <Copy className={`w-3 h-3 ${copiedId ? 'text-green-500' : ''}`} />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={copyNameToClipboard}
              title={copiedName ? "Name Copied!" : "Copy Name"}
              className="h-6 w-6 text-purple-600 hover:text-purple-700 hover:bg-purple-50 dark:text-purple-400 dark:hover:bg-purple-950 flex-shrink-0"
            >
              <FileText className={`w-3 h-3 ${copiedName ? 'text-green-500' : ''}`} />
            </Button>

            <div className="w-2 h-2 rounded-full bg-blue-400 dark:bg-blue-600 flex-shrink-0"></div>
            <span className="text-gray-700 dark:text-gray-300 font-medium">{summary.title}</span>
            {summary.progress_percentage !== undefined && (
              <Badge variant="outline" className="text-xs bg-gray-100 dark:bg-gray-800/50 border-gray-300 dark:border-gray-700">
                {summary.status === 'done' ? 100 : summary.progress_percentage}%
              </Badge>
            )}
          </div>
        </TableCell>

        {/* Status column - align with parent */}
        <TableCell className="hidden sm:table-cell">
          <HolographicStatusBadge status={summary.status as any} size="xs" />
        </TableCell>

        {/* Priority column - align with parent */}
        <TableCell className="hidden md:table-cell">
          <HolographicPriorityBadge priority={summary.priority as any} size="xs" />
        </TableCell>

        {/* Dependencies column - empty for subtasks to maintain alignment */}
        <TableCell className="hidden lg:table-cell">
          <span className="text-xs text-muted-foreground">-</span>
        </TableCell>

        {/* Assignees column - align with parent */}
        <TableCell className="hidden md:table-cell max-w-[200px] p-2 align-top">
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

        {/* Actions column - align with parent */}
        <TableCell className="">
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                handleViewDetails();
              }}
              disabled={isLoading}
              title="View details"
              className="h-8 w-8"
            >
              {isLoading ? (
                <div className="w-3 h-3 border border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onSubtaskAction('edit', summary.id);
              }}
              disabled={isLoading || summary.status === 'done'}
              title="Edit"
              className="h-8 w-8"
            >
              <Pencil className="w-4 h-4" />
            </Button>

            {summary.status !== 'done' && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onSubtaskAction('complete', summary.id);
                }}
                disabled={isLoading}
                title="Complete"
                className="h-8 w-8"
              >
                <Check className="w-4 h-4" />
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSubtask(summary.id);
              }}
              title="Delete subtask"
              className="h-8 w-8"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </TableCell>
      </TableRow>

      {/* Subtask Details Row */}
      {showDetails && fullSubtask && (
        <TableRow className="bg-blue-50/30 dark:bg-blue-950/10">
          <TableCell colSpan={7} className="pl-12">
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