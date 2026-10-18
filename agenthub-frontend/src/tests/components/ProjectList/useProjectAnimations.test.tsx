import React from 'react';
import { render, act } from '@testing-library/react';
import { vi, describe, it, expect, afterEach } from 'vitest';
import { useProjectAnimations } from '../../../components/ProjectList/hooks/useProjectAnimations';

/**
 * The /dashboard React update-depth bailout (board task 2e756846) came from this hook: it kept the
 * previous counts in state and wrote that state on every effect run, so an equal-but-fresh
 * `taskCounts` (what `useBranchSummaries` hands its consumer while the query has no data -
 * `data?.branches ?? []`) re-rendered the consumer, re-ran the effect and never settled.
 */

const Probe: React.FC<{ counts: Record<string, number> }> = ({ counts }) => {
  const { animatingCounts } = useProjectAnimations({ taskCounts: counts });
  return <div data-testid="animating">{JSON.stringify(Array.from(animatingCounts))}</div>;
};

describe('useProjectAnimations', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('settles when taskCounts is a new but equal object on every render', async () => {
    let renders = 0;
    // The input turns stable after 20 renders, so the loop this guards against stops on its own and
    // the assertion below is the failure - an unbounded red run would OOM the runner instead of
    // reporting.
    const stable: Record<string, number> = {};
    const Unstable: React.FC = () => {
      renders += 1;
      useProjectAnimations({ taskCounts: renders <= 20 ? {} : stable });
      return null;
    };

    render(<Unstable />);
    // The loop it replaced never yielded; a bounded window is enough to see the difference.
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(renders).toBeLessThan(5);
  });

  it('animates a real count change and clears it after the animation', () => {
    vi.useFakeTimers();
    const { rerender, getByTestId } = render(<Probe counts={{ branch1: 3 }} />);
    expect(getByTestId('animating').textContent).toBe('[]');

    rerender(<Probe counts={{ branch1: 5 }} />);
    expect(getByTestId('animating').textContent).toBe('[["branch1","up"]]');

    act(() => {
      vi.advanceTimersByTime(600);
    });
    expect(getByTestId('animating').textContent).toBe('[]');
  });

  it('reports a decreasing count as down', () => {
    vi.useFakeTimers();
    const { rerender, getByTestId } = render(<Probe counts={{ branch1: 9 }} />);
    rerender(<Probe counts={{ branch1: 4 }} />);
    expect(getByTestId('animating').textContent).toBe('[["branch1","down"]]');
  });

  it('clears an earlier branch when a second one changes mid-animation', () => {
    vi.useFakeTimers();
    const { rerender, getByTestId } = render(<Probe counts={{ branch1: 3, branch2: 0 }} />);

    rerender(<Probe counts={{ branch1: 5, branch2: 0 }} />);
    act(() => {
      vi.advanceTimersByTime(300);
    });

    rerender(<Probe counts={{ branch1: 5, branch2: 2 }} />);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(getByTestId('animating').textContent).toBe('[["branch2","up"]]');

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(getByTestId('animating').textContent).toBe('[]');
  });
});
