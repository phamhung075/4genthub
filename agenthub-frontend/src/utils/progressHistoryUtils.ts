/**
 * Utility functions for parsing and handling progress history
 */

import type { ProgressEntry } from '../types/utilityTypes';

/**
 * Parse the joined progress history into individual progress entries
 * @param progressHistory - The joined history text (`details`): "=== Progress N ===\n<content>" blocks
 * @returns Array of progress entries with number and content
 */
export function parseProgressHistory(progressHistory?: string): ProgressEntry[] {
  if (!progressHistory) return [];

  // The served field is ONE joined string: `details` renders the column's notes merged with the
  // ledger's. The object shape this used to accept came from a payload the server stopped sending,
  // and a reader that accepted both could not tell which one a note came from.
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
 * @param progressHistory - The joined history text (`details`)
 * @returns Latest progress content or empty string
 */
export function getLatestProgress(progressHistory?: string): string {
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
  const cleaned = text
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
 * @param progressHistory - The joined history text (`details`)
 * @param maxLength - Maximum length for summary
 * @returns Summary of latest progress with clean formatting
 */
export function getProgressSummary(progressHistory?: string, maxLength: number = 100): string {
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
