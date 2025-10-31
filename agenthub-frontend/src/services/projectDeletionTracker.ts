import logger from '../utils/logger';

/**
 * Global tracker for projects pending deletion
 * Used to coordinate delete animations across components
 */
class ProjectDeletionTracker {
  private pendingDeletions = new Set<string>();

  markForDeletion(projectId: string): void {
    logger.debug('🗑️ [ProjectDeletionTracker] Marking project for deletion:', projectId);
    this.pendingDeletions.add(projectId);
  }

  isMarkedForDeletion(projectId: string): boolean {
    return this.pendingDeletions.has(projectId);
  }

  clearDeletion(projectId: string): void {
    this.pendingDeletions.delete(projectId);
  }

  getPendingDeletions(): string[] {
    return Array.from(this.pendingDeletions);
  }
}

export const projectDeletionTracker = new ProjectDeletionTracker();
