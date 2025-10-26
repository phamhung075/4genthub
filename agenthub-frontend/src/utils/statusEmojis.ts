/**
 * Client-side emoji mapping utilities
 * Replaces backend emoji fields removed in Phase 1 API optimization
 */

/**
 * Maps task/subtask priority to emoji
 */
export function getPriorityEmoji(priority: string): string {
  const emojiMap: Record<string, string> = {
    'critical': '🔴',
    'high': '🔴',
    'urgent': '🔴',
    'medium': '🟡',
    'low': '🟢',
  };
  return emojiMap[priority.toLowerCase()] ?? '⚪';
}

/**
 * Maps task/subtask status to emoji
 */
export function getStatusEmoji(status: string): string {
  const emojiMap: Record<string, string> = {
    'todo': '📋',
    'in_progress': '⚙️',
    'blocked': '🚫',
    'review': '👀',
    'testing': '🧪',
    'done': '✅',
    'completed': '✅',
    'cancelled': '❌',
  };
  return emojiMap[status.toLowerCase()] ?? '❓';
}

/**
 * Optional: Combined function for convenience
 */
export function getEntityEmoji(entity: {
  status?: string;
  priority?: string;
}, type: 'status' | 'priority'): string {
  if (type === 'status' && entity.status) {
    return getStatusEmoji(entity.status);
  }
  if (type === 'priority' && entity.priority) {
    return getPriorityEmoji(entity.priority);
  }
  return '⚪';
}
