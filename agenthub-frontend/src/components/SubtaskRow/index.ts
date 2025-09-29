// SubtaskRow module barrel exports
export { default } from './SubtaskRowRefactored';
export { default as SubtaskRow } from './SubtaskRowRefactored';

// Export components for reuse
export { SubtaskRowActions } from './components/SubtaskRowActions';
export { SubtaskRowBadges } from './components/SubtaskRowBadges';
export { SubtaskRowAssignees } from './components/SubtaskRowAssignees';

// Export hooks for testing
export { useSubtaskAnimation } from './hooks/useSubtaskAnimation';

// Types are exported from src/types/subtaskTypes.ts