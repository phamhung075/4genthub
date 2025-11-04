// LazySubtaskList constants
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

/**
 * Animation configuration
 */
export const ANIMATION_CONFIG = {
  // Duration for row animations
  ROW_ANIMATION_DURATION: 300,
  // Delay between multiple animations
  ANIMATION_STAGGER_DELAY: 50,
  // Timeout for animation cleanup
  ANIMATION_CLEANUP_TIMEOUT: 500
} as const;

/**
 * Loading states configuration
 */
export const LOADING_CONFIG = {
  // Initial load delay to prevent flashing
  INITIAL_LOAD_DELAY: 100,
  // Debounce delay for rapid updates - INCREASED to 2500ms to handle sequential MCP subtask creation
  // Backend creates subtasks at ~400-500ms each, so 5 subtasks = ~2 seconds total
  // This ensures API fallback waits for ALL subtasks to be created before fetching
  UPDATE_DEBOUNCE_DELAY: 2500,
  // Timeout for stale data refresh
  REFRESH_TIMEOUT: 30000
} as const;

/**
 * Dialog configuration
 */
export const DIALOG_CONFIG = {
  // Timeout to prevent race conditions in dialog opening
  DIALOG_RACE_TIMEOUT: 100,
  // Auto-close timeout for success messages
  SUCCESS_MESSAGE_TIMEOUT: 3000
} as const;