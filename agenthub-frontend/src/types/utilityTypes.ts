/**
 * Utility Types
 * Centralized type definitions for utility functions and helper modules
 */

// =============================================================================
// Progress History Types
// =============================================================================

/**
 * Progress entry structure for display
 */
export interface ProgressEntry {
  number: number;
  content: string;
  timestamp?: string;
}

/**
 * Backend progress history entry format
 */
export interface ProgressHistoryEntry {
  content: string;
  timestamp: string;
  progress_number: number;
}

/**
 * Progress history object format from backend
 */
export interface ProgressHistoryObject {
  [key: string]: ProgressHistoryEntry;
}