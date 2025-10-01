/**
 * Global tracker for tasks pending deletion
 * Used to coordinate delete animations across components
 */
class TaskDeletionTracker {
  private pendingDeletions = new Set<string>();

  markForDeletion(taskId: string): void {
    logger.debug('🗑️ [TaskDeletionTracker] Marking task for deletion:', taskId);
    this.pendingDeletions.add(taskId);
  }

  isMarkedForDeletion(taskId: string): boolean {
    return this.pendingDeletions.has(taskId);
  }

  clearDeletion(taskId: string): void {
    this.pendingDeletions.delete(taskId);
  }

  getPendingDeletions(): string[] {
    return Array.from(this.pendingDeletions);
  }
}

export const taskDeletionTracker = new TaskDeletionTracker();
