import { useState, useCallback } from 'react';
import type { DialogType, ActiveDialog } from '../../../types/taskTypes';

export interface UseDialogManagerReturn {
  activeDialog: ActiveDialog;
  openDialog: (type: string, taskId?: string, extraData?: any) => void;
  closeDialog: () => void;
  saving: boolean;
  setSaving: (saving: boolean) => void;
}

export function useDialogManager(
  urlTaskId?: string,
  subtaskId?: string,
  onNavigateBack?: () => void,
  onLoadFullTask?: (taskId: string) => void,
  onLoadAgents?: () => void
): UseDialogManagerReturn {
  const [activeDialog, setActiveDialog] = useState<ActiveDialog>({ type: null });
  const [saving, setSaving] = useState(false);

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
  }, [onLoadFullTask, onLoadAgents]);

  const closeDialog = useCallback(() => {
    // If there's a taskId in URL (meaning we opened via URL)
    if (urlTaskId && onNavigateBack) {
      // If there's also a subtaskId, we're viewing a subtask - don't navigate away
      if (subtaskId) {
        // Just close the task dialog locally without navigation
        setActiveDialog({ type: null });
      } else {
        // Navigate back to branch URL only if there's no subtask being viewed
        onNavigateBack();
        // Don't call setActiveDialog here - let the component handle it when URL changes
      }
    } else {
      // Direct dialog opening (not via URL), close normally
      setActiveDialog({ type: null });
    }
  }, [urlTaskId, subtaskId, onNavigateBack]);

  return {
    activeDialog,
    openDialog,
    closeDialog,
    saving,
    setSaving
  };
}
