// OWNER BUG (b), SECOND HALF: after the dialog has been open once, the NEXT View-details click
// opens and closes it instantly - the owner's "needs two clicks". TaskRowDetailsOneClick.test.tsx
// guards the first open at this fidelity; this file guards every open AFTER it, plus the two paths
// the fix must not break (a deep link, and a URL transition back to the branch).
//
// THE BUG, MEASURED (fe-dev, 2026-10-08, on the tree before the fix):
//   useDialogManager.openDialog sets the dialog state AND navigates, and the two commit in SEPARATE
//   renders. So one render carries `activeDialog.type === 'details'` while `urlTaskId` is still
//   undefined. The URL-sync effect in LazyTaskListRefactored was subscribed to `activeDialog.type`
//   (it was in the dependency array), so it RAN on that intermediate render; comparing `urlTaskId`
//   against `lastProcessedTaskIdRef` - which still held the id of the PREVIOUS open - it read the
//   pair (undefined, 'details') as a back-navigation and called closeDialog(), destroying the dialog
//   it had just been asked to open. The URL had meanwhile reached /task/<id>, so the result was the
//   owner's permanent desync: a task URL, no dialog, and the next click harmless because the failed
//   open had left the ref clear.
// EXACTLY ONE closeDialog per close, by the way: an earlier note in that row counted FOUR, which was
// an artifact of matching the substring 'close' across the logger's other lines.
//
// THE FIX (3176a4af), in the two shapes this file pins:
//   1. the URL-sync effect reads the dialog type from a REF and no longer depends on it, so it runs
//      on URL transitions only and can never observe an intermediate dialog-state render;
//   2. the CLOSE branch requires a real transition - a PREVIOUS urlTaskId that was DEFINED and a
//      current one that is not - so undefined-in-both can never close; and the transition is consumed
//      before the isClosingRef early return, so it cannot be re-read later and misapplied to a new open.
//   3. a close's deferred writes are cancelled by the next open (useDialogManager), because otherwise
//      a dialog opened inside the close's 50ms window is wiped by the close that preceded it.
//
// THE HARNESS is the same fidelity as TaskRowDetailsOneClick.test.tsx: only the process boundaries
// are mocked (network, auth, toasts, the websocket transport, the logger) and the REAL react-query
// client, useTasks/useTaskMutations, useDialogManager, DialogSection, Dialog and TaskDetailsDialog
// run, with the router set up the way App.tsx sets it up - both the branch and the task path render
// the SAME element, so nothing remounts on the transition.
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const TASK = vi.hoisted(() => ({
  id: 'task-1',
  title: 'A task whose details are viewed',
  status: 'todo',
  priority: 'medium',
  git_branch_id: 'b1',
  project_id: 'p1',
  assignees: [],
  labels: [],
  has_dependencies: false,
  has_context: false,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T00:00:00Z',
  subtask_count: 0,
  completed_subtasks: 0,
}));

vi.mock('../../api', () => ({
  getTasks: vi.fn().mockResolvedValue({ tasks: [TASK] }),
  getTask: vi.fn().mockResolvedValue(TASK),
  getTaskContext: vi.fn().mockResolvedValue(null),
  getAvailableAgents: vi.fn().mockResolvedValue([]),
  getCurrentUserId: vi.fn().mockReturnValue('u1'),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
  completeTask: vi.fn(),
  updateTaskContext: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u1' }, tokens: { access_token: 't' } }),
}));

// THE TOAST BOUNDARY, pointed at the REAL module (src/components/ui/toast): the path used to be
// '../ui/toast', which resolves to src/tests/ui/toast — nonexistent — so this factory shielded nothing
// and the real hooks ran. Ruled by the lead: aim it rather than delete it.
vi.mock('../../components/ui/toast', () => ({
  useErrorToast: () => vi.fn(),
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));

// The transport boundary: no socket exists under jsdom, so this is stated rather than hidden.
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: () => ({ isConnected: false, client: null }),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import LazyTaskListRefactored from '../../components/LazyTaskList/LazyTaskListRefactored';

let queryClient: QueryClient;
// A router-driven URL change with no app-side close: the same shape the browser back button
// produces, and the only way to reach the close branch the fix keeps for it.
let navigateRef: ((to: string) => void) | null = null;

function Probe() {
  const navigate = useNavigate();
  navigateRef = (to: string) => navigate(to);
  return null;
}

const BRANCH_URL = '/dashboard/project/p1/branch/b1';
const TASK_URL = BRANCH_URL + '/task/task-1';

function renderList(initialPath: string) {
  window.history.pushState({}, '', initialPath);
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Probe />
        <Routes>
          {/* THE SAME ELEMENT FOR BOTH PATHS, as App.tsx has it: nothing remounts on the transition. */}
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId/task/:taskId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

async function clickViewDetailsAndWaitForDialog() {
  fireEvent.click(await screen.findByTitle('View details'));
  return screen.findByRole('dialog', {}, { timeout: 2000 });
}

// Sample for 500ms and record whether the dialog is ever ABSENT. "Still open after a tick" is
// satisfied by a close-and-reopen, which is exactly what the owner reports as "closes instantly".
async function sampleDialogPresence() {
  const samples: string[] = [];
  for (let i = 0; i < 10; i++) {
    await act(async () => {
      await new Promise(r => setTimeout(r, 50));
    });
    samples.push(screen.queryByRole('dialog') ? 'OPEN' : 'ABSENT');
  }
  return samples;
}

describe('the details dialog opens on ONE click, on a fresh mount and on every later open', () => {
  beforeEach(() => {
    queryClient?.clear();
  });

  afterEach(() => {
    queryClient?.clear();
  });

  it('opens on one click from a fresh mount', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();

    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
    expect(window.location.pathname).toBe(TASK_URL);
  });

  it('opens on one click again AFTER a dialog has been closed - the owner\u2019s two clicks', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();
    expect(window.location.pathname).toBe(TASK_URL);

    // Close it the way a user does: the full-viewport overlay.
    fireEvent.click(document.querySelector('.theme-modal-overlay') as HTMLElement);
    expect(window.location.pathname).toBe(BRANCH_URL);

    // THE OWNER'S CLICK: the next View-details must open it and KEEP it open.
    await clickViewDetailsAndWaitForDialog();

    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
    expect(window.location.pathname).toBe(TASK_URL);
  });

  it('opens on one click again when the previous close is still in flight (inside its 50ms window)', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();

    fireEvent.click(document.querySelector('.theme-modal-overlay') as HTMLElement);

    // No wait: the close's deferred state clear has not run yet, and must not be allowed to wipe
    // the dialog this click is opening.
    await clickViewDetailsAndWaitForDialog();

    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
  });

  it('opens from a deep link on mount', async () => {
    renderList(TASK_URL);

    await screen.findByRole('dialog', {}, { timeout: 2000 });
    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
    expect(window.location.pathname).toBe(TASK_URL);
  });

  it('still closes when the URL transitions back to the branch, as the back button does', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();
    expect(window.location.pathname).toBe(TASK_URL);

    // No closeDialog() call anywhere in the app: a bare URL transition, which is all the back button
    // is. This is the path the fix deliberately keeps.
    await act(async () => {
      navigateRef?.(BRANCH_URL);
    });

    // closeDialog clears the dialog state on a 50ms timer by design (it lets the navigation land
    // first), so the close is observed by waiting rather than on the next tick.
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(window.location.pathname).toBe(BRANCH_URL);
  });
});
