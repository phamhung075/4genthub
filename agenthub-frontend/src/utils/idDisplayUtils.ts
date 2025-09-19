// Utility functions for displaying IDs and copying them to clipboard

/**
 * Abbreviates a UUID for display while keeping enough characters for identification
 * @param id The full UUID to abbreviate
 * @param length The number of characters to show from start and end (default: 8)
 * @returns Abbreviated ID string
 */
export const abbreviateId = (id: string, length: number = 8): string => {
  if (!id || id.length <= length * 2) {
    return id;
  }

  const start = id.substring(0, length);
  const end = id.substring(id.length - length);
  return `${start}...${end}`;
};

/**
 * Copies text to clipboard
 * @param text The text to copy
 * @returns Promise that resolves to boolean indicating success
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    // Fallback for older browsers
    try {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const result = document.execCommand('copy');
      document.body.removeChild(textArea);
      return result;
    } catch (fallbackError) {
      console.error('Failed to copy to clipboard:', fallbackError);
      return false;
    }
  }
};

/**
 * Formats an ID for display with copy functionality
 * @param id The ID to format
 * @param label The label to show before the ID (e.g., "ID:", "Subtask:")
 * @param abbreviated Whether to show abbreviated version
 * @returns Object with display text and full ID
 */
export const formatIdForDisplay = (
  id: string,
  label: string = '',
  abbreviated: boolean = true
) => {
  const displayId = abbreviated ? abbreviateId(id) : id;
  const displayText = label ? `${label} ${displayId}` : displayId;

  return {
    displayText,
    fullId: id,
    abbreviatedId: displayId
  };
};