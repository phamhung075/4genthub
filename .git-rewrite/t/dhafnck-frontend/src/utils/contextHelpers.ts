// Utility functions for handling context data structure changes
// Supports both new (progress.current_session_summary) and legacy (progress.completion_summary) formats

export interface ContextProgress {
  current_session_summary?: string;
  completion_summary?: string; // Legacy field
  completion_percentage?: number;
  next_steps?: string[];
  completed_actions?: string[];
}

export interface ContextMetadata {
  status?: string;
  [key: string]: any;
}

export interface ContextData {
  progress?: ContextProgress;
  metadata?: ContextMetadata;
  [key: string]: any;
}

/**
 * Extract completion summary from context data, handling both new and legacy formats
 */
export function getCompletionSummary(contextData?: ContextData): string | null {
  if (!contextData?.progress) return null;
  
  // Prefer new format
  if (contextData.progress.current_session_summary) {
    return contextData.progress.current_session_summary;
  }
  
  // Fall back to legacy format
  if (contextData.progress.completion_summary) {
    return contextData.progress.completion_summary;
  }
  
  return null;
}

/**
 * Check if context data is using legacy format
 */
export function isLegacyFormat(contextData?: ContextData): boolean {
  if (!contextData?.progress) return false;
  
  return !contextData.progress.current_session_summary && 
         !!contextData.progress.completion_summary;
}

/**
 * Get completion percentage from context data
 */
export function getCompletionPercentage(contextData?: ContextData): number | null {
  return contextData?.progress?.completion_percentage ?? null;
}

/**
 * Get task status from metadata
 */
export function getTaskStatus(contextData?: ContextData): string | null {
  return contextData?.metadata?.status ?? null;
}

/**
 * Get testing notes and next steps as an array
 */
export function getTestingNotes(contextData?: ContextData): string[] {
  if (!contextData?.progress?.next_steps) return [];
  
  return Array.isArray(contextData.progress.next_steps) 
    ? contextData.progress.next_steps 
    : [];
}

/**
 * Check if context data has meaningful completion information
 */
export function hasCompletionInfo(contextData?: ContextData): boolean {
  return !!(
    getCompletionSummary(contextData) ||
    getTaskStatus(contextData) ||
    getTestingNotes(contextData).length > 0
  );
}

/**
 * Format context data for display with proper labels
 */
export function formatContextDisplay(contextData?: ContextData) {
  const completionSummary = getCompletionSummary(contextData);
  const isLegacy = isLegacyFormat(contextData);
  const completionPercentage = getCompletionPercentage(contextData);
  const taskStatus = getTaskStatus(contextData);
  const testingNotes = getTestingNotes(contextData);
  
  return {
    completionSummary,
    isLegacy,
    completionPercentage,
    taskStatus,
    testingNotes,
    hasInfo: hasCompletionInfo(contextData)
  };
}