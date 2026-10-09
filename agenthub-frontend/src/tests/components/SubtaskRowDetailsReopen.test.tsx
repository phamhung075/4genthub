// OWNER BUG (b) IN THE SUBTASK LIST: the same two-click defect the task list carried, confirmed by
// reproduction rather than by structural resemblance. Row 5320f3ce.
//
// IT WAS RED FIRST, AND THE RED WAS THE POINT: on the unmodified tree this file reports
// 1 failed | 4 passed - only "opens on one click again AFTER a dialog has been closed" fails, with
// assertion 'expected [ "ABSENT", "ABSENT", ... x10 ] to deeply equal [ Array(10) ]', while fresh
// mount, deep link and the back transition stay GREEN. That signature is what separates the defect
// from a broken harness; when all four go red, suspect the instrument first.
//
// THE MECHANISM, MEASURED, AND IT IS NOT THE TWIN'S: useSubtaskDialogs.ts's close schedules its state
// clear on a 50ms timer that nothing can cancel, so a dialog OPENED inside that window is set and then
// wiped by the close that preceded it. The trace shows the dialog flag going true -> false while the
// URL is already correct, so the write that kills it is the CLOSE's deferral, not the URL-sync effect.
// THE PRE-FIX SHAPE THE REVIEWER IDENTIFIED IS GENUINELY PRESENT here - the stale
// lastProcessedSubtaskIdRef, the snapshot gate, detailsDialog.open among the effect's dependencies, and
// :149's isClosingRef early return BEFORE the ref write at :155 - and an ablation shows it is NOT what
// this defect needs: with only the effect change the file is still 1 failed | 4 passed, with only the
// hook change it is 5 passed. So the effect change was applied, measured and CUT, and the code in
// LazySubtaskListRefactored.tsx below is the twin's pre-fix shape, deliberately unchanged.
//
// THE FIX IS ONE CHANGE: useSubtaskDialogs.ts's close is cancellable and openDetailsDialog cancels it,
// so a dialog opened inside the close's 50ms window is no longer wiped by the close that preceded it.
// Nothing in LazySubtaskListRefactored.tsx changed - the ablation above is why.
//
// ONE FIXTURE DETAIL IS LOAD-BEARING RATHER THAN COSMETIC: SubtaskDetailsDialog.tsx:52 tests the
// subtask id against /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i and
// calls onOpenChange(false) when it fails, so an id like 'sub-1' makes the REAL dialog close itself
// the instant it opens - which turns every case red and looks exactly like the defect.
//
// FIDELITY: only the process boundaries are mocked (the network via ../../api and ../../api-lazy,
// auth, toasts, the websocket transport, the logger, and the animation hook whose timers would
// outlive the test); the REAL react-query client, useSubtasks, useSubtaskFilters, useSubtaskExpansion,
// useSubtaskDialogs, SubtaskListContent, SubtaskRow, SubtaskDialogs and the REAL lazily-loaded
// SubtaskDetailsDialog all run, with both the branch and the subtask path rendering the SAME element
// as App.tsx has it.
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const SUB = vi.hoisted(() => ({
  // A valid UUID; see the note above - the dialog validates this and closes itself on failure.
  id: '11111111-2222-4333-8444-555555555555',
  title: 'A subtask whose details are viewed',
  description: 'The description the details dialog shows.',
  status: 'todo',
  priority: 'medium',
  parent_task_id: 'task-1',
  git_branch_id: 'b1',
  progress_percentage: 0,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T00:00:00Z',
  assignees: [],
  labels: [],
  progress_history: {},
  subtask_count: 0,
  completed_subtasks: 0,
}));

vi.mock('../../api', () => ({
  listSubtasks: vi.fn().mockResolvedValue([SUB]),
  getSubtask: vi.fn().mockResolvedValue(SUB),
  getSubtaskSummaries: vi.fn().mockResolvedValue({ subtasks: [SUB] }),
  completeSubtask: vi.fn().mockResolvedValue(SUB),
  createSubtask: vi.fn().mockResolvedValue(SUB),
  deleteSubtask: vi.fn().mockResolvedValue(undefined),
  updateSubtask: vi.fn().mockResolvedValue(SUB),
  getTask: vi.fn().mockResolvedValue(null),
  getTaskContext: vi.fn().mockResolvedValue(null),
  getAvailableAgents: vi.fn().mockResolvedValue([]),
  getCurrentUserId: vi.fn().mockReturnValue('u1'),
}));

vi.mock('../../api-lazy', () => ({
  getSubtaskSummaries: vi.fn().mockResolvedValue({ subtasks: [SUB] }),
  getSubtaskSummary: vi.fn().mockResolvedValue(SUB),
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

// The transport boundary: no socket exists under jsdom, so this is stated rather than hidden.
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: () => ({ isConnected: false, client: null }),
}));

// The animation hook's timers would otherwise fire after teardown.
vi.mock('../../hooks/useSubtaskAnimation', () => ({
  useSubtaskAnimation: () => ({
    animationState: 'none',
    isVisible: true,
    animationClass: '',
    elementRef: { current: null },
    hasPlayedCreateAnimation: true,
    playCreateAnimation: vi.fn(),
    playUpdateAnimation: vi.fn(),
    playDeleteAnimation: vi.fn(),
  }),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

// The barrel export, which is how the existing LazySubtaskList test imports it: the component file
// exports a NAMED export and the barrel supplies the default.
import LazySubtaskListRefactored from '../../components/LazySubtaskList';

let queryClient: QueryClient;
// A router-driven URL change with no app-side close: the shape the back button produces, and the only
// way to reach the close branch the fix deliberately keeps.
let navigateRef: ((to: string) => void) | null = null;

function Probe() {
  const navigate = useNavigate();
  navigateRef = (to: string) => navigate(to);
  return null;
}

const BRANCH_URL = '/dashboard/project/p1/branch/b1';
const SUBTASK_URL = BRANCH_URL + '/subtask/' + SUB.id;

function renderList(initialPath: string) {
  window.history.pushState({}, '', initialPath);
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const element = <LazySubtaskListRefactored projectId="p1" taskTreeId="b1" parentTaskId="task-1" />;
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Probe />
        <Routes>
          {/* THE SAME ELEMENT FOR BOTH PATHS, as App.tsx has it: nothing remounts on the transition. */}
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId" element={element} />
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId/subtask/:subtaskId" element={element} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

async function clickViewDetailsAndWaitForDialog() {
  fireEvent.click(await screen.findByTitle('View details'));
  return screen.findByRole('dialog', {}, { timeout: 3000 });
}

async function closeViaOverlay() {
  const overlay = document.querySelector('.theme-modal-overlay') as HTMLElement;
  expect(overlay).toBeTruthy();
  fireEvent.click(overlay);
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

describe('the subtask details dialog opens on ONE click, on a fresh mount and on every later open', () => {
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
    expect(window.location.pathname).toBe(SUBTASK_URL);
  });

  it('opens from a deep link on mount', async () => {
    renderList(SUBTASK_URL);

    await screen.findByRole('dialog', {}, { timeout: 3000 });
    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
    expect(window.location.pathname).toBe(SUBTASK_URL);
  });

  it('opens on one click again AFTER a dialog has been closed - the reproduced two clicks', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();
    expect(window.location.pathname).toBe(SUBTASK_URL);

    await closeViaOverlay();
    expect(window.location.pathname).toBe(BRANCH_URL);

    // THE REPRODUCED CLICK: the next View-details must open it and KEEP it open.
    await clickViewDetailsAndWaitForDialog();

    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
    expect(window.location.pathname).toBe(SUBTASK_URL);
  });

  it('opens again once the previous close has settled - the boundary where ONLY the deferred clear matters', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();

    await closeViaOverlay();
    // Past every timer the close scheduled, so only the stale-ref half can be responsible here.
    await act(async () => {
      await new Promise(r => setTimeout(r, 300));
    });

    await clickViewDetailsAndWaitForDialog();

    expect(await sampleDialogPresence()).toEqual(Array(10).fill('OPEN'));
  });

  it('still closes when the URL transitions back to the branch, as the back button does', async () => {
    renderList(BRANCH_URL);
    await clickViewDetailsAndWaitForDialog();
    expect(window.location.pathname).toBe(SUBTASK_URL);

    // No close handler runs anywhere in the app: a bare URL transition, which is all the back button
    // is. This is the path the fix deliberately keeps.
    await act(async () => {
      navigateRef?.(BRANCH_URL);
    });

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(window.location.pathname).toBe(BRANCH_URL);
  });
});
