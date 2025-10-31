import logger from '../utils/logger';

/**
 * Global tracker for branches pending deletion
 * Used to coordinate delete animations across components
 */
class BranchDeletionTracker {
  private pendingDeletions = new Set<string>();

  markForDeletion(branchId: string): void {
    logger.debug('🗑️ [BranchDeletionTracker] Marking branch for deletion:', branchId);
    this.pendingDeletions.add(branchId);
  }

  isMarkedForDeletion(branchId: string): boolean {
    return this.pendingDeletions.has(branchId);
  }

  clearDeletion(branchId: string): void {
    this.pendingDeletions.delete(branchId);
  }

  getPendingDeletions(): string[] {
    return Array.from(this.pendingDeletions);
  }
}

export const branchDeletionTracker = new BranchDeletionTracker();
