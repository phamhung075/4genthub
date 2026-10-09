// OWNER BUG (b): the View-details dialog needs TWO clicks. THIS FILE IS A GUARD, NOT A REPRODUCTION - and
// the distinction is the point of the file.
//
// IT PASSES ON TODAY'S TREE, AND ITS FIRST RUN DID NOT: that first run reported the owner's flash exactly
// (the dialog present when awaited, then ABSENT in all ten 50ms samples), and the log carried
// "No getTaskContext export is defined on the ../../api mock" - the now-REAL TaskDetailsDialog was throwing
// on an incomplete mock, so the ABSENT samples were the harness failing, not the app. With that one export
// added the case is green. A FAILING READING FROM A BROKEN INSTRUMENT IS NOT A FINDING, which is why the
// mock below spells out every export the real tree imports.
//
// WHAT IT MEASURES NOW: that ONE click on View details opens the dialog and it is the SAME DOM NODE across
// the next 500ms. That is the boundary an earlier guard (LazyTaskListDialogOpen.test.tsx) also established,
// and this file establishes it with the stubs removed: it mocks ONLY the process boundaries - the network
// (../../api), auth, toasts, the websocket transport (no socket exists under jsdom) and the logger - and runs
// the REAL react-query client, the REAL useTasks/useTaskMutations, the REAL useDialogManager, the REAL
// DialogSection, the REAL Dialog and the REAL TaskDetailsDialog, with the router set up the way App.tsx sets
// it up.
//
// AND THE NAMED GAP, SO THE NEXT READER DOES NOT RE-DERIVE IT: jsdom cannot produce this bug. The one
// candidate the code supports is ui/dialog.tsx:32 - the overlay is a FULL-VIEWPORT
// <div onClick={() => onOpenChange(false)}> with no guard against the gesture that opened it, shared by every
// dialog in the app. For the opening gesture to be read as a dismiss, a pointerdown/mousedown must be in
// flight while the overlay mounts. jsdom dispatches ONE synthetic click with no such sequence, and the
// overlay mounts after it completes, so the condition is unreachable here however faithful the component
// tree is. Confirming it needs the real browser; a more elaborate jsdom harness will not do it.
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// vi.mock factories are HOISTED above every top-level binding, so the fixture they close over has to be
// hoisted with them - a plain `const TASK = {...}` here fails at collection time.
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

// THE NETWORK BOUNDARY, mocked. Everything above it is real.
vi.mock('../../api', () => ({
  getTasks: vi.fn().mockResolvedValue({ tasks: [TASK] }),
  getTask: vi.fn().mockResolvedValue(TASK),
  // The REAL TaskDetailsDialog imports this; leaving it out made the harness throw and would have made
  // the result untrustworthy, so it is spelled out rather than assumed unused.
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

// THE TRANSPORT BOUNDARY: no socket exists under jsdom, so this is stated rather than hidden.
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: () => ({ isConnected: false, client: null }),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import LazyTaskListRefactored from '../../components/LazyTaskList/LazyTaskListRefactored';

let queryClient: QueryClient;

function renderList(initialPath: string) {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          {/* THE SAME ELEMENT FOR BOTH PATHS, as App.tsx has it. */}
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
          <Route path="/dashboard/project/:projectId/branch/:taskTreeId/task/:taskId" element={<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('the details dialog after ONE click, at full fidelity', () => {
  beforeEach(() => {
    queryClient?.clear();
  });

  afterEach(() => {
    queryClient?.clear();
  });

  it('is open after a single View-details click and stays the same node', async () => {
    renderList('/dashboard/project/p1/branch/b1');

    const view = await screen.findByTitle('View details');
    fireEvent.click(view);

    // The lazy TaskDetailsDialog resolves in a microtask; wait for the dialog to exist at all.
    const opened = await screen.findByRole('dialog', {}, { timeout: 2000 });

    // NOW THE PART THAT CATCHES THE OWNER'S FLASH: sample for 500ms and record whether the dialog is ever
    // ABSENT, and whether the node identity changes. "Still open after a tick" is satisfied by a
    // close-and-reopen, which is exactly what the owner reports as "opens and closes instantly".
    const samples: string[] = [];
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 50));
      const node = screen.queryByRole('dialog');
      samples.push(node ? (node === opened ? 'same' : 'different-node') : 'ABSENT');
      if (document.querySelector('.theme-modal-overlay') === null) samples.push('overlay-gone');
    }

    expect(samples.filter(s => s !== 'same' && s !== 'overlay-gone')).toEqual([]);
  });
});
