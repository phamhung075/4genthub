import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { DialogType, ActiveDialog } from '../../../types/taskTypes';
import type { UseDialogManagerReturn } from '../../../types/hookTypes';
import logger from '../../../utils/logger';

export function useDialogManager(
  projectId: string,
  taskTreeId: string,
  urlTaskId?: string,
  subtaskId?: string,
  onLoadFullTask?: (taskId: string) => void,
  onLoadAgents?: () => void
): UseDialogManagerReturn {
  const navigate = useNavigate();
  const [activeDialog, setActiveDialog] = useState<ActiveDialog>({ type: null });
  const [saving, setSaving] = useState(false);

  // Track if we're in the middle of closing to prevent race conditions
  const isClosingRef = useRef(false);

  const openDialog = useCallback((type: string, taskId?: string, extraData?: any) => {
    // Set dialog state immediately to fix double-click issue
    setActiveDialog({ type: type as DialogType, taskId, data: extraData });

    // Load data asynchronously after dialog is opened
    if (taskId && onLoadFullTask) {
      onLoadFullTask(taskId);
    }

    if (type === 'assign' && onLoadAgents) {
      onLoadAgents();
    }

    // Navigate to task URL only for details dialog
    if (type === 'details' && taskId) {
      navigate(`/dashboard/project/${projectId}/branch/${taskTreeId}/task/${taskId}`);
    }
  }, [navigate, projectId, taskTreeId, onLoadFullTask, onLoadAgents]);

  const closeDialog = useCallback(() => {
    logger.debug('Starting dialog close process');

    // Set closing flag to prevent useEffect from reopening
    isClosingRef.current = true;

    // If there's a taskId in URL (meaning we opened via URL), navigate back
    if (urlTaskId) {
      // If there's also a subtaskId, we're viewing a subtask - don't navigate away
      if (!subtaskId) {
        // Navigate first to remove taskId from URL
        const branchUrl = `/dashboard/project/${projectId}/branch/${taskTreeId}`;
        navigate(branchUrl);
        logger.debug('Navigated to branch URL:', branchUrl);
      }
    }

    // Use setTimeout to allow navigation to complete before clearing state
    setTimeout(() => {
      // Clear dialog state
      setActiveDialog({ type: null });

      // Reset closing flag after state updates complete
      setTimeout(() => {
        isClosingRef.current = false;
        logger.debug('Dialog close complete, reopening protection reset');
      }, 100);
    }, 50);
  }, [navigate, projectId, taskTreeId, urlTaskId, subtaskId]);

  return {
    activeDialog,
    openDialog,
    closeDialog,
    saving,
    setSaving,
    isClosingRef // Expose ref for race condition prevention
  };
}
