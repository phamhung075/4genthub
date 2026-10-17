// THE BOARD FILTERS BY SEAT, AND IT FILTERS BEFORE THE PAGE CAP. The second half is the part a
// screen-level test must prove and a unit test of the predicate cannot: TASKS_PER_PAGE is 20, so a
// board whose only fe-dev task sits at index 20 shows "no tasks" for that seat if the slice runs
// first. The scenario below puts exactly that task at index 20 and asserts it is reachable by
// selecting the seat and absent without the filter.
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import type * as ReactQuery from '@tanstack/react-query';
import LazyTaskListRefactored from '../../components/LazyTaskList/LazyTaskListRefactored';

vi.mock('../../api', () => ({
  getAvailableAgents: vi.fn().mockResolvedValue([]),
  getTask: vi.fn().mockResolvedValue(null),
  getCurrentUserId: vi.fn().mockReturnValue('u1'),
}));
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u1' }, tokens: { access_token: 't' } }),
}));
vi.mock('../../components/ui/toast', () => ({
  useErrorToast: () => vi.fn(),
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: () => ({ isConnected: false, client: null }),
}));
vi.mock('../../hooks/useRealtimeSync', () => ({ useRealtimeSync: vi.fn() }));

const TASKS = [
  ...Array.from({ length: 20 }, (_, i) => ({
    id: `lead-task-${i}`,
    title: `Lead task ${i}`,
    status: 'todo',
    priority: 'medium',
    git_branch_id: 'branch-1',
    assignees: ['@lead'],
    subtask_count: 0,
  })),
  {
    id: 'fe-task-1',
    title: 'A task only fe-dev owns',
    status: 'todo',
    priority: 'high',
    git_branch_id: 'branch-1',
    assignees: ['@fe-dev'],
    subtask_count: 0,
  },
];

vi.mock('../../hooks/useTasks', () => ({
  useTasks: () => ({
    data: TASKS,
    isLoading: false,
    refetch: vi.fn(),
  }),
  useTask: () => ({ data: undefined, isLoading: false }),
  useTaskMutations: () => ({}),
}));
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof ReactQuery>('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({ fetchQuery: vi.fn(), invalidateQueries: vi.fn() }),
  };
});

function renderList() {
  return render(
    <MemoryRouter initialEntries={['/dashboard/project/p1/branch/b1']}>
      <Routes>
        <Route
          path="/dashboard/project/:projectId/branch/:taskTreeId"
          element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />}
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('the board filters by seat', () => {
  it('reaches a seat whose only task lies past the page cap, and hides it again', async () => {
    renderList();

    // The page cap holds 20 rows, and the fe-dev task is the 21st: unfiltered, it is not shown.
    expect(await screen.findByText('Tasks (21)')).toBeInTheDocument();
    expect(screen.queryByText('A task only fe-dev owns')).not.toBeInTheDocument();

    // Both seats named on the board are offered, in the '@<seat_key>' form the rows carry.
    const select = screen.getByLabelText('Filter by seat') as HTMLSelectElement;
    const options = Array.from(select.options).map(option => option.value);
    expect(options).toEqual(['all', '@fe-dev', '@lead']);

    fireEvent.change(select, { target: { value: '@fe-dev' } });

    await waitFor(() => {
      expect(screen.getByText('A task only fe-dev owns')).toBeInTheDocument();
    });
    expect(screen.getByText('Tasks (1 of 21)')).toBeInTheDocument();
    expect(screen.queryByText('Lead task 0')).not.toBeInTheDocument();

    // Back to every seat: the capped page returns and the 21st row goes with it.
    fireEvent.change(select, { target: { value: 'all' } });

    await waitFor(() => {
      expect(screen.getByText('Tasks (21)')).toBeInTheDocument();
    });
    expect(screen.queryByText('A task only fe-dev owns')).not.toBeInTheDocument();
    expect(screen.getByText('Lead task 0')).toBeInTheDocument();
  });
});
