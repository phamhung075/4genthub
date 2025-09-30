// useSubtaskDialogs hook - Dialog state management for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Subtask } from "../../../api";
import type {
  UseSubtaskDialogsReturn,
  DeleteDialogState,
  ActiveDialogState,
  DetailsDialogState
} from "../../../types/subtaskTypes";
import { generateBranchUrl } from "../utils/subtaskHelpers";
import { DIALOG_CONFIG } from "../constants/subtaskConstants";
import logger from "../../../utils/logger";

/**
 * Custom hook for managing all dialog states in LazySubtaskList
 * Handles create, edit, details, delete, complete, and agent info dialogs
 */
export function useSubtaskDialogs(
  projectId: string,
  taskTreeId: string
): UseSubtaskDialogsReturn {

  const navigate = useNavigate();

  // Dialog states
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState>({
    open: false,
    subtaskId: null
  });

  const [activeDialog, setActiveDialog] = useState<ActiveDialogState>({
    type: null
  });

  const [detailsDialog, setDetailsDialog] = useState<DetailsDialogState>({
    open: false,
    subtask: null
  });

  const [selectedAgentForInfo, setSelectedAgentForInfo] = useState<string | null>(null);
  const [agentInfoDialogOpen, setAgentInfoDialogOpen] = useState(false);
  const [createSubtaskDialogOpen, setCreateSubtaskDialogOpen] = useState(false);

  /**
   * Handle subtask dialog close - navigate back to branch URL
   */
  const handleSubtaskDialogClose = useCallback(() => {
    // Close the details dialog first
    setDetailsDialog({ open: false, subtask: null });

    // Clear any active dialog state
    setActiveDialog({ type: null });

    const branchUrl = generateBranchUrl(projectId, taskTreeId);
    navigate(branchUrl);

    logger.debug('Closed details dialog and navigated back to branch URL:', branchUrl);
  }, [navigate, projectId, taskTreeId]);

  /**
   * Handle agent info click
   */
  const handleAgentInfoClick = useCallback((agentName: string) => {
    logger.debug('Agent info clicked:', agentName);

    setSelectedAgentForInfo(agentName);
    setAgentInfoDialogOpen(true);

    logger.debug('Agent info dialog opened for:', agentName);
  }, []);

  /**
   * Handle opening create subtask dialog
   */
  const handleOpenCreateSubtask = useCallback(() => {
    logger.debug('Opening create subtask dialog');
    setCreateSubtaskDialogOpen(true);
  }, []);

  /**
   * Open details dialog for a subtask
   */
  const openDetailsDialog = useCallback((subtask: Subtask) => {
    logger.debug('Opening details dialog for subtask:', subtask.id);

    setDetailsDialog({
      open: true,
      subtask
    });

    setActiveDialog({
      type: 'details',
      subtaskId: subtask.id,
      subtask
    });
  }, []);

  /**
   * Open edit dialog for a subtask
   */
  const openEditDialog = useCallback((subtask: Subtask) => {
    logger.debug('Opening edit dialog for subtask:', subtask.id);

    setActiveDialog({
      type: 'edit',
      subtaskId: subtask.id,
      subtask
    });
  }, []);

  /**
   * Open complete dialog for a subtask
   */
  const openCompleteDialog = useCallback((subtask: Subtask) => {
    logger.debug('Opening complete dialog for subtask:', subtask.id);

    setActiveDialog({
      type: 'complete',
      subtaskId: subtask.id,
      subtask
    });
  }, []);

  /**
   * Open delete confirmation dialog
   */
  const openDeleteDialog = useCallback((subtaskId: string) => {
    logger.debug('Opening delete dialog for subtask:', subtaskId);

    setDeleteDialog({
      open: true,
      subtaskId
    });
  }, []);

  /**
   * Close delete dialog
   */
  const closeDeleteDialog = useCallback(() => {
    logger.debug('Closing delete dialog');

    setDeleteDialog({
      open: false,
      subtaskId: null
    });
  }, []);

  /**
   * Close details dialog
   */
  const closeDetailsDialog = useCallback(() => {
    logger.debug('Closing details dialog');

    setDetailsDialog({
      open: false,
      subtask: null
    });

    // Clear active dialog if it was details
    setActiveDialog(prev =>
      prev.type === 'details' ? { type: null } : prev
    );
  }, []);

  /**
   * Close agent info dialog
   */
  const closeAgentInfoDialog = useCallback(() => {
    logger.debug('Closing agent info dialog');

    setAgentInfoDialogOpen(false);
    setSelectedAgentForInfo(null);
  }, []);

  /**
   * Close create subtask dialog
   */
  const closeCreateSubtaskDialog = useCallback(() => {
    logger.debug('Closing create subtask dialog');
    setCreateSubtaskDialogOpen(false);
  }, []);

  /**
   * Close all dialogs
   */
  const closeAllDialogs = useCallback(() => {
    logger.debug('Closing all dialogs');

    setDeleteDialog({ open: false, subtaskId: null });
    setActiveDialog({ type: null });
    setDetailsDialog({ open: false, subtask: null });
    setAgentInfoDialogOpen(false);
    setSelectedAgentForInfo(null);
    setCreateSubtaskDialogOpen(false);
  }, []);

  /**
   * Handle dialog action with race condition protection
   */
  const handleDialogAction = useCallback((
    action: 'details' | 'edit' | 'complete',
    subtaskId: string,
    subtask?: Subtask
  ) => {
    // Prevent race conditions
    setTimeout(() => {
      logger.debug(`Opening ${action} dialog for subtask:`, subtaskId);

      setActiveDialog({
        type: action,
        subtaskId,
        subtask: subtask || null
      });
    }, DIALOG_CONFIG.DIALOG_RACE_TIMEOUT);
  }, []);

  /**
   * Check if any dialog is open
   */
  const hasOpenDialog =
    deleteDialog.open ||
    detailsDialog.open ||
    agentInfoDialogOpen ||
    createSubtaskDialogOpen ||
    activeDialog.type !== null;

  return {
    // Dialog states
    deleteDialog,
    activeDialog,
    detailsDialog,
    selectedAgentForInfo,
    agentInfoDialogOpen,
    createSubtaskDialogOpen,

    // Navigation handlers
    handleSubtaskDialogClose,

    // Dialog openers
    handleAgentInfoClick,
    handleOpenCreateSubtask,
    openDetailsDialog,
    openEditDialog,
    openCompleteDialog,
    openDeleteDialog,

    // Dialog closers
    closeDeleteDialog,
    closeDetailsDialog,
    closeAgentInfoDialog,
    closeCreateSubtaskDialog,
    closeAllDialogs,

    // Utility handlers
    handleDialogAction,

    // State helpers
    hasOpenDialog
  };
}