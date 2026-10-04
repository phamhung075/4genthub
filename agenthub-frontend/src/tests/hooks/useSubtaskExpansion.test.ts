import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSubtaskExpansion } from '../../components/LazySubtaskList/hooks/useSubtaskExpansion';
import { ANIMATION_CONFIG } from '../../components/LazySubtaskList/constants/subtaskConstants';
import type { SubtaskSummary } from '../../types/taskTypes';

const one: SubtaskSummary = { id: 'sub-1', title: 'One', status: 'todo', priority: 'medium' };
const two: SubtaskSummary = { id: 'sub-2', title: 'Two', status: 'todo', priority: 'low' };
// Stable references: the hook re-runs its change effect whenever the array identity changes
const oneList = [one];
const none: SubtaskSummary[] = [];
const changedList = [{ ...one, title: 'One renamed' }, two];

describe('useSubtaskExpansion', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('leaves no pending trigger-clear timer after unmount', () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() => useSubtaskExpansion(oneList));
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });

  it('auto-clears the opening-dialog flag, and cancels that timer on unmount', () => {
    vi.useFakeTimers();
    const { result, unmount } = renderHook(() => useSubtaskExpansion(none));

    act(() => result.current.setIsOpeningDialog(true));
    expect(result.current.isOpeningDialog).toBe(true);
    act(() => {
      vi.advanceTimersByTime(ANIMATION_CONFIG.ANIMATION_CLEANUP_TIMEOUT);
    });
    expect(result.current.isOpeningDialog).toBe(false);

    act(() => result.current.setIsOpeningDialog(true));
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('cancels the staggered create and update animation timers on unmount', () => {
    vi.useFakeTimers();
    const { rerender, unmount } = renderHook(({ list }) => useSubtaskExpansion(list), {
      initialProps: { list: oneList },
    });
    act(() => {
      vi.runAllTimers();
    });
    expect(vi.getTimerCount()).toBe(0);

    // sub-2 is created and sub-1 is updated: two stagger timers plus the trigger-clear timer
    rerender({ list: changedList });
    expect(vi.getTimerCount()).toBe(3);

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });

  it('registers no timer when the opening-dialog flag is set after unmount', () => {
    vi.useFakeTimers();
    const { result, unmount } = renderHook(() => useSubtaskExpansion(none));
    unmount();

    result.current.setIsOpeningDialog(true);

    expect(vi.getTimerCount()).toBe(0);
  });
});
