// ProjectList hooks barrel export
export { useProjectDialogs } from './useProjectDialogs';
export { useProjectAnimations } from './useProjectAnimations';

// Re-export types from centralized types (hookTypes)
export type {
  UseProjectDialogsReturn,
  UseProjectAnimationsReturn,
  UseProjectAnimationsOptions,
  ProjectDialogType
} from '../../../types/hookTypes';

// Re-export component types
export type { ProjectFormData, DeleteBranchDialogState } from '../../../types/componentTypes';
