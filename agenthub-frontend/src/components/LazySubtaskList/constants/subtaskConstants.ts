// LazySubtaskList constants
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import type { BadgeVariant } from "../types/subtaskTypes";

/**
 * Status color mapping for badges
 * Maps subtask status to UI badge variant
 */
export const STATUS_COLOR_MAP: Record<string, BadgeVariant> = {
  done: "default",
  in_progress: "secondary",
  review: "secondary",
  testing: "secondary",
  todo: "outline",
  blocked: "destructive",
  cancelled: "destructive",
  archived: "outline"
} as const;

/**
 * Priority color mapping for badges
 * Maps subtask priority to UI badge variant
 */
export const PRIORITY_COLOR_MAP: Record<string, BadgeVariant> = {
  low: "outline",
  medium: "secondary",
  high: "default",
  urgent: "destructive"
} as const;

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
  // Debounce delay for rapid updates
  UPDATE_DEBOUNCE_DELAY: 150,
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