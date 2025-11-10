// SubtaskListContent component - Main table content for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useEffect } from "react";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "../../ui/table";
import { SubtaskSummary } from "../../../types/taskTypes";
import { Subtask } from "../../../api";
import SubtaskRow from "../../SubtaskRow";
import type { RowAnimationCallbacks } from "../../../types/subtaskTypes";
import logger from "../../../utils/logger";

interface SubtaskListContentProps {
  subtaskSummaries: SubtaskSummary[];
  fullSubtasks: Map<string, Subtask>;
  loadingSubtasks: Set<string>;
  showDetails: string | null;
  parentTaskId: string;
  onSubtaskAction: (action: 'details' | 'edit' | 'complete', subtaskId: string) => void;
  onAgentInfoClick: (agentName: string) => void;
  onDeleteSubtask: (subtaskId: string) => void;
  onRegisterCallbacks: (subtaskId: string, callbacks: RowAnimationCallbacks) => void;
  onUnregisterCallbacks: (subtaskId: string) => void;
}

/**
 * Content component for the subtask list table
 * Renders the table structure and individual subtask rows
 */
export function SubtaskListContent({
  subtaskSummaries,
  fullSubtasks,
  loadingSubtasks,
  showDetails,
  parentTaskId,
  onSubtaskAction,
  onAgentInfoClick,
  onDeleteSubtask,
  onRegisterCallbacks,
  onUnregisterCallbacks
}: SubtaskListContentProps) {

  // Debug logging to track rendering
  useEffect(() => {
    logger.debug('🎨 [SubtaskListContent] Rendering subtasks', {
      count: subtaskSummaries.length,
      subtaskIds: subtaskSummaries.map(s => s.id),
      subtaskTitles: subtaskSummaries.map(s => s.title)
    });
  }, [subtaskSummaries]);

  /**
   * Render individual subtask row
   */
  const renderSubtaskRow = (summary: SubtaskSummary) => {
    const isLoadingFull = loadingSubtasks.has(summary.id);
    const isShowingDetails = showDetails === summary.id;
    const fullSubtask = fullSubtasks.get(summary.id);

    return (
      <SubtaskRow
        key={summary.id}
        summary={summary}
        fullSubtask={fullSubtask || null}
        isLoading={isLoadingFull}
        showDetails={isShowingDetails}
        parentTaskId={parentTaskId}
        onSubtaskAction={onSubtaskAction}
        onAgentInfoClick={onAgentInfoClick}
        onDeleteSubtask={(subtaskId) => onDeleteSubtask(subtaskId)}
        onRegisterCallbacks={onRegisterCallbacks}
        onUnregisterCallbacks={onUnregisterCallbacks}
      />
    );
  };

  return (
    <Table className="bg-white/50 dark:bg-gray-900/50 rounded-lg overflow-hidden">
      <TableHeader>
        <TableRow className="bg-gray-100/50 dark:bg-gray-800/20 border-b border-gray-200 dark:border-gray-700">
          {/* Empty header for expand button column alignment */}
          <TableHead className="w-[50px]"></TableHead>
          <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">
            Title
          </TableHead>
          <TableHead className="hidden sm:table-cell text-xs text-blue-700 dark:text-blue-300 font-semibold">
            Status
          </TableHead>
          <TableHead className="hidden md:table-cell text-xs text-blue-700 dark:text-blue-300 font-semibold">
            Priority
          </TableHead>
          <TableHead className="hidden md:table-cell text-xs text-blue-700 dark:text-blue-300 font-semibold">
            Assignees
          </TableHead>
          <TableHead className="text-xs text-blue-700 dark:text-blue-300 font-semibold">
            Actions
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {subtaskSummaries.map(renderSubtaskRow)}
      </TableBody>
    </Table>
  );
}

export default SubtaskListContent;