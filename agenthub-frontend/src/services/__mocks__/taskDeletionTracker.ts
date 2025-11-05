import { vi } from 'vitest';

export const taskDeletionTracker = {
  markForDeletion: vi.fn(),
  isMarkedForDeletion: vi.fn().mockReturnValue(false),
  clearDeletion: vi.fn(),
  getPendingDeletions: vi.fn().mockReturnValue([]),
};
