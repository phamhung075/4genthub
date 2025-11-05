import { vi } from 'vitest';

export const branchDeletionTracker = {
  markForDeletion: vi.fn(),
  isMarkedForDeletion: vi.fn().mockReturnValue(false),
  clearDeletion: vi.fn(),
  getPendingDeletions: vi.fn().mockReturnValue([]),
};
