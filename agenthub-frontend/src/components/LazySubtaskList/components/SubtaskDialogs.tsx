// SubtaskDialogs component - All dialog components for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { Suspense, lazy } from "react";
import { Subtask } from "../../../api";
import { SubtaskSummary } from "../../../types/taskTypes";
import { Button } from "../../ui/button";
import SubtaskCreateDialog from "../../SubtaskCreateDialog";
import type {
  DeleteDialogState,
  ActiveDialogState,
  DetailsDialogState
} from "../../../types/subtaskTypes";
import logger from "../../../utils/logger";

// Lazy load heavy dialog components
const DeleteConfirmDialog = lazy(() => import("../../DeleteConfirmDialog"));
const SubtaskCompleteDialog = lazy(() => import("../../SubtaskCompleteDialog"));
const SubtaskEditDialog = lazy(() => import("../../SubtaskEditDialog"));
const SubtaskDetailsDialog = lazy(() => import("../../SubtaskDetailsDialog"));
const AgentInfoDialog = lazy(() => import("../../AgentInfoDialog"));

interface SubtaskDialogsProps {
  // Dialog states
  deleteDialog: DeleteDialogState;
  activeDialog: ActiveDialogState;
  detailsDialog: DetailsDialogState;
  selectedAgentForInfo: string | null;
  agentInfoDialogOpen: boolean;
  createSubtaskDialogOpen: boolean;
  editingSubtask: Subtask | null;
  isOpeningDialog: boolean;

  // Data
  subtaskSummaries: SubtaskSummary[];
  parentTaskId: string;

  // Dialog handlers
  onDeleteDialogChange: (open: boolean) => void;
  onActiveDialogChange: (dialog: ActiveDialogState) => void;
  onAgentInfoDialogChange: (open: boolean) => void;
  onCreateDialogChange: (open: boolean) => void;
  onEditingSubtaskChange: (subtask: Subtask | null) => void;

  // Action handlers
  onDeleteSubtask: (subtaskId: string) => Promise<void>;
  onCompleteSubtask: (subtask: Subtask) => void;
  onSubtaskCreated: (subtask: Subtask) => void;
  onSubtaskDialogClose: () => void;

  // Agent dialog handlers
  onAgentInfoClose: () => void;
  onSelectedAgentChange: (agent: string | null) => void;
}

/**
 * All dialogs component for the subtask list
 * Manages rendering of all dialog types with lazy loading
 */
export function SubtaskDialogs({
  deleteDialog,
  activeDialog,
  detailsDialog,
  selectedAgentForInfo,
  agentInfoDialogOpen,
  createSubtaskDialogOpen,
  editingSubtask,
  isOpeningDialog,
  subtaskSummaries,
  parentTaskId,
  onDeleteDialogChange,
  onActiveDialogChange,
  onAgentInfoDialogChange,
  onCreateDialogChange,
  onEditingSubtaskChange,
  onDeleteSubtask,
  onCompleteSubtask,
  onSubtaskCreated,
  onSubtaskDialogClose,
  onAgentInfoClose,
  onSelectedAgentChange
}: SubtaskDialogsProps) {

  return (
    <>
      {/* Create Subtask Dialog - Not lazy loaded for better UX */}
      <SubtaskCreateDialog
        open={createSubtaskDialogOpen}
        onOpenChange={onCreateDialogChange}
        parentTaskId={parentTaskId}
        onClose={() => onCreateDialogChange(false)}
        onCreated={onSubtaskCreated}
      />

      {/* Lazy-loaded dialogs */}
      <Suspense fallback={null}>
        {/* Delete Confirmation Dialog */}
        {deleteDialog.open && deleteDialog.subtaskId && (
          <DeleteConfirmDialog
            open={deleteDialog.open}
            onOpenChange={onDeleteDialogChange}
            onConfirm={() => {
              if (deleteDialog.subtaskId) {
                onDeleteSubtask(deleteDialog.subtaskId);
              }
            }}
            title="Delete Subtask"
            description="Are you sure you want to delete this subtask? This action cannot be undone."
            itemName={subtaskSummaries.find(s => s.id === deleteDialog.subtaskId)?.title}
          />
        )}

        {/* Complete Subtask Dialog */}
        {activeDialog.type === 'complete' && activeDialog.subtask && (
          <SubtaskCompleteDialog
            open={true}
            onOpenChange={(open) => {
              if (!open) {
                onActiveDialogChange({ type: null });
              }
            }}
            subtask={activeDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={() => onActiveDialogChange({ type: null })}
            onComplete={onCompleteSubtask}
          />
        )}

        {/* Edit Subtask Dialog */}
        {activeDialog.type === 'edit' && activeDialog.subtask && (
          <SubtaskEditDialog
            open={true}
            onOpenChange={(open) => {
              if (!open) {
                onActiveDialogChange({ type: null });
              }
            }}
            subtask={activeDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={() => onActiveDialogChange({ type: null })}
            onUpdated={(updatedSubtask) => {
              logger.debug('Subtask updated:', updatedSubtask);
              // No need to manually refresh - WebSocket will handle it
            }}
          />
        )}

        {/* Subtask Details Dialog */}
        {detailsDialog.open && (
          <SubtaskDetailsDialog
            open={detailsDialog.open}
            onOpenChange={(open) => {
              if (!open && !isOpeningDialog) {
                // Only handle close events when we're not in the process of opening
                // This prevents race conditions during dialog initialization
                onSubtaskDialogClose();
              }
            }}
            subtask={detailsDialog.subtask}
            parentTaskId={parentTaskId}
            onClose={onSubtaskDialogClose}
          />
        )}

        {/* Agent Info Dialog */}
        {selectedAgentForInfo && (
          <>
            {logger.debug('🚀 Rendering AgentInfoDialog:', {
              agentName: selectedAgentForInfo,
              open: agentInfoDialogOpen,
              taskTitle: `Subtask: ${subtaskSummaries.find(s => s.assignees?.includes(selectedAgentForInfo))?.title || ''}`
            })}
            <AgentInfoDialog
              open={agentInfoDialogOpen}
              onOpenChange={onAgentInfoDialogChange}
              agentName={selectedAgentForInfo}
              taskTitle={`Subtask: ${subtaskSummaries.find(s => s.assignees?.includes(selectedAgentForInfo))?.title || ''}`}
              onClose={() => {
                logger.debug('🔒 Closing AgentInfoDialog');
                onAgentInfoDialogChange(false);
                onSelectedAgentChange(null);
                onAgentInfoClose();
              }}
            />
          </>
        )}
      </Suspense>
    </>
  );
}

export default SubtaskDialogs;