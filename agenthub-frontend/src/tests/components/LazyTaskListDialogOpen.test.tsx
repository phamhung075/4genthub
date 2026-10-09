// THIS TEST DOES NOT REPRODUCE THE OWNER'S BUG, AND ITS HEADER SAYS SO RATHER THAN
// IMPLYING OTHERWISE. It renders the REAL LazyTaskListRefactored with the real
// useDialogManager and a real click on View details, and the dialog is still there -
// same DOM NODE - after the timers. What it therefore establishes is a BOUNDARY: at this
// level of fidelity, with two routes that reconcile to the same element, no close or
// remount occurs. The owner's "opens and closes instantly" needs something this harness
// does not have, and the candidate narrowed to during the investigation is the ROUTE
// ELEMENT IDENTITY: useDialogManager.openDialog navigates to /.../task/<id> for 'details',
// and if the real router mounts a DIFFERENT element for that path the list remounts, the
// dialog state is destroyed, and the URL-sync effect's other branch reopens it - a flash
// the owner would see as "closes instantly", while a SECOND click (same URL, no route
// change) leaves it alone. That is a hypothesis with a named test to settle it, not a
// finding: it was NOT reproduced here, and it is recorded as unproven.
//
// WHY THIS LEVEL rather than the row alone: the dialog's state lives in useDialogManager,
// held by the LIST, and a test that mocked the manager (as the seat-loading test does)
// would stub out the very state under test.
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import LazyTaskListRefactored from '../../components/LazyTaskList/LazyTaskListRefactored';

vi.mock('../../api', () => ({
  getAvailableAgents: vi.fn().mockResolvedValue([]),
  getTask: vi.fn().mockResolvedValue(null),
  getCurrentUserId: vi.fn().mockReturnValue('u1'),
  getSubtaskSummaries: vi.fn().mockResolvedValue({ subtasks: [] }),
  fetchTasks: vi.fn().mockResolvedValue([]),
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
  useTaskWebSocket: () => ({ isConnected: false, client: null }),
  useWebSocketV2: () => ({ isConnected: false, client: null }),
}));
vi.mock('../../hooks/useRealtimeSync', () => ({ useRealtimeSync: vi.fn() }));

const TASK = {
  id: 'task-1',
  title: 'A task whose details are viewed',
  status: 'todo',
  priority: 'medium',
  git_branch_id: 'branch-1',
  assignees: [],
  subtask_count: 0,
};

vi.mock('../../hooks/useTasks', () => ({
  useTasks: () => ({
    data: [{ ...TASK }],
    isLoading: false,
    refetch: vi.fn(),
  }),
  // The details dialog now subscribes to ['task', taskId, false] through useTask. The mocked
  // module has to carry the export, and undefined data deliberately leaves the dialog on its
  // task PROP, which is the path this case exercises.
  useTask: () => ({ data: undefined, isLoading: false }),
  useTaskMutations: () => ({}),
}));
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({ fetchQuery: vi.fn(), invalidateQueries: vi.fn() }),
  };
});

function renderList(initialPath = '/dashboard/project/p1/branch/b1') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/dashboard/project/:projectId/branch/:taskTreeId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
        <Route path="/dashboard/project/:projectId/branch/:taskTreeId/task/:taskId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('the task row dialog must stay open after ONE click', () => {
  it('keeps the details dialog open after a single View-details click', async () => {
    renderList();

    const view = await screen.findByTitle('View details');

    // ONE click. Not two - the bug is that the first one opens and instantly closes.
    fireEvent.click(view);

    // THE ASSERTION THE ACCEPTANCE NAMES, SHARPENED: "still open after a tick" is satisfied
    // by a CLOSE-AND-REOPEN, which is exactly what the owner sees as "opens and closes
    // instantly". A remount replaces the node, so the identity is what separates staying
    // open from flashing.
    await waitFor(
      () => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      },
      { timeout: 1500 }
    );

    const nodeAfterOpen = screen.getByRole('dialog');

    await new Promise((r) => setTimeout(r, 300));

    expect(screen.getByRole('dialog')).toBe(nodeAfterOpen);
  });
});
