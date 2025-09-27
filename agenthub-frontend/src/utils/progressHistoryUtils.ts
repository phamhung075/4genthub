/**
 * Utility functions for parsing and handling progress history
 */

export interface ProgressEntry {
  number: number;
  content: string;
  timestamp?: string;
}

// Interface for the new backend progress history object format
interface ProgressHistoryEntry {
  content: string;
  timestamp: string;
  progress_number: number;
}

interface ProgressHistoryObject {
  [key: string]: ProgressHistoryEntry;
}

/**
 * Parse progress history from either string (legacy) or object (new format) into individual progress entries
 * @param progressHistory - Progress history in either string or object format from backend
 * @returns Array of progress entries with number and content
 */
export function parseProgressHistory(progressHistory?: string | ProgressHistoryObject): ProgressEntry[] {
  if (!progressHistory) return [];

  // Handle new object format
  if (typeof progressHistory === 'object' && progressHistory !== null) {
    const entries: ProgressEntry[] = [];

    // Extract all entries from the object
    Object.values(progressHistory).forEach((entry: ProgressHistoryEntry) => {
      if (entry && entry.content && typeof entry.progress_number === 'number') {
        entries.push({
          number: entry.progress_number,
          content: entry.content,
          timestamp: entry.timestamp,
        });
      }
    });

    // Sort by progress number
    return entries.sort((a, b) => a.number - b.number);
  }

  // Handle legacy string format - backward compatibility
  if (typeof progressHistory === 'string') {
    const entries: ProgressEntry[] = [];
    const sections = progressHistory.split(/=== Progress (\d+) ===/).filter(Boolean);

    for (let i = 0; i < sections.length; i += 2) {
      const numberStr = sections[i];
      const content = sections[i + 1];

      if (numberStr && content) {
        const number = parseInt(numberStr, 10);
        const trimmedContent = content.trim();

        if (!isNaN(number) && trimmedContent) {
          entries.push({
            number,
            content: trimmedContent,
          });
        }
      }
    }

    return entries.sort((a, b) => a.number - b.number);
  }

  return [];
}

/**
 * Get the latest progress entry content
 * @param progressHistory - Progress history in either string or object format from backend
 * @returns Latest progress content or empty string
 */
export function getLatestProgress(progressHistory?: string | ProgressHistoryObject): string {
  const entries = parseProgressHistory(progressHistory);
  return entries.length > 0 ? entries[entries.length - 1].content : '';
}

/**
 * Clean progress text by removing ugly formatting markers
 * @param text - Raw progress text that may contain === Progress X === markers
 * @returns Cleaned text without formatting markers
 */
export function cleanProgressText(text: string): string {
  if (!text) return '';

  // Remove === Progress X === headers and similar patterns
  let cleaned = text
    .replace(/^=+\s*Progress\s+\d+\s*=+\s*$/gm, '') // Remove === Progress N === lines
    .replace(/^#+\s*Progress\s+\d+\s*$/gm, '') // Remove ## Progress N headers
    .replace(/^-+\s*Progress\s+\d+\s*-+\s*$/gm, '') // Remove --- Progress N --- lines
    .replace(/^\*+\s*Progress\s+\d+\s*\*+\s*$/gm, '') // Remove *** Progress N *** lines
    .replace(/^\s*\n/gm, '') // Remove empty lines at start
    .trim();

  // If the text starts with a markdown header, extract the meaningful content
  const lines = cleaned.split('\n').filter(line => line.trim() !== '');
  if (lines.length === 0) return '';

  // Skip markdown headers and get to the actual content
  let startIndex = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('#') || line.startsWith('*') || line.startsWith('-')) {
      continue;
    }
    startIndex = i;
    break;
  }

  return lines.slice(startIndex).join('\n').trim();
}

/**
 * Get a summary of the latest progress (first line or truncated) with cleaned formatting
 * @param progressHistory - Progress history in either string or object format from backend
 * @param maxLength - Maximum length for summary
 * @returns Summary of latest progress with clean formatting
 */
export function getProgressSummary(progressHistory?: string | ProgressHistoryObject, maxLength: number = 100): string {
  const latestProgress = getLatestProgress(progressHistory);
  if (!latestProgress) return '';

  // Clean the progress text first
  const cleanedProgress = cleanProgressText(latestProgress);
  if (!cleanedProgress) return '';

  // Get first meaningful line
  const firstLine = cleanedProgress.split('\n')[0].trim();
  if (!firstLine) return '';

  if (firstLine.length <= maxLength) {
    return firstLine;
  }

  // Truncate at word boundary when possible
  const truncated = firstLine.substring(0, maxLength - 3);
  const lastSpace = truncated.lastIndexOf(' ');
  if (lastSpace > maxLength * 0.7) { // Only use word boundary if it's not too short
    return truncated.substring(0, lastSpace) + '...';
  }

  return truncated + '...';
}

/**
 * Format progress entry for display with proper styling classes
 * @param entry - Progress entry to format
 * @param index - Index for alternating styles
 * @returns Formatted entry with CSS classes
 */
export function formatProgressEntryForDisplay(entry: ProgressEntry, index: number) {
  const isEven = index % 2 === 0;
  return {
    ...entry,
    cssClasses: isEven ? 'bg-gray-50 dark:bg-gray-800/50' : 'bg-white dark:bg-gray-900/50',
    borderClasses: 'border-l-4 border-blue-400 dark:border-blue-500',
  };
}