import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSubtaskExpansion } from '../../components/LazySubtaskList/hooks/useSubtaskExpansion';
import type { SubtaskSummary } from '../../types/taskTypes';

const summaries: SubtaskSummary[] = [{ id: 'sub-1', title: 'One', status: 'todo', priority: 'medium' }];

describe('useSubtaskExpansion', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('leaves no pending trigger-clear timer after unmount', () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() => useSubtaskExpansion(summaries));
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });
});
