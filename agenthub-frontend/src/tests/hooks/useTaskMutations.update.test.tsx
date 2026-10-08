// OWNER BUG (a): THE CASE THAT FAILS ON TODAY'S TREE.
//
// THE OWNER'S SENTENCE: "task UPDATE does not trigger the row animation or the status change in the
// frontend, while CREATE works." This file pins the status half, at the moment the owner described:
// after the user updates a task from the LIST, the list the row reads must show the new status
// WITHOUT waiting for a server round trip. CREATE has exactly that guarantee - createMutation.onMutate
// inserts the new task into ['tasks', newTask.git_branch_id] - and UPDATE does not.
//
// WHY IT DOES NOT, from reading the code rather than assuming it: updateMutation.onMutate resolves the
// branch as
//     const git_branch_id = previousTask?.git_branch_id || updates.git_branch_id;
// where previousTask comes from the INDIVIDUAL cache ['task', taskId, false] - which a list page never
// fills, because nothing fetches a single task until the details dialog is opened - and api.ts's
// updateTask does not send a branch either (its payload filter lists title/description/status/priority/
// progress_percentage/assignees/labels/estimated_effort/due_date/dependencies/context_data/details and
// NOT git_branch_id). So BOTH halves are undefined on the path the UI actually uses, and the
// `if (previousTasks && git_branch_id)` guard skips the optimistic list write entirely.
//
// THE HARNESS SEEDS ONLY WHAT A LIST PAGE HAS: ['tasks', <branch>], and nothing else. A harness that
// also seeded ['task', id, false] would PASS on today's tree and would therefore prove nothing about
// the bug the owner reported - that seed is the fidelity that has to be absent for this test to mean
// anything.
//
// NOT A REFETCH TEST, ON PURPOSE: the mocked updateTask never settles inside the assertion window, so
// the ONLY thing that can have put the new status in the list cache at that moment is the optimistic
// write. That is what makes a failure here a statement about the UI rather than about a mocked server.
import React from 'react';
import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../api', () => ({
  getTasks: vi.fn().mockResolvedValue({ tasks: [] }),
  getTask: vi.fn().mockResolvedValue(null),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
  completeTask: vi.fn(),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import { createTask, updateTask } from '../../api';
import { useTaskMutations } from '../../hooks/useTasks';
import type { Task } from '../../types/api.types';

const BRANCH = 'branch-1';

const task: Task = {
  id: 't1',
  title: 'a task on a list page',
  description: '',
  status: 'todo',
  priority: 'medium',
  git_branch_id: BRANCH,
  project_id: 'p1',
  assignees: [],
  labels: [],
  has_dependencies: false,
  has_context: false,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T00:00:00Z',
  subtask_count: 0,
  completed_subtasks: 0,
} as Task;

describe("updating a task moves the row the list page renders", () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
  });

  afterEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it('shows the new status in the list before the round trip finishes, as CREATE already does', async () => {
    // A list page has exactly this much: the branch list. Nothing has opened this task's dialog,
    // so ['task', 't1', false] does not exist.
    queryClient.setQueryData<Task[]>(['tasks', BRANCH], [task]);
    expect(queryClient.getQueryData(['task', 't1', false])).toBeUndefined();

    // The round trip stays OPEN across the assertion, so a refetch cannot be the explanation.
    vi.mocked(updateTask).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useTaskMutations(), { wrapper });

    await act(async () => {
      void result.current.updateTaskAsync({ taskId: 't1', updates: { status: 'in_progress' } });
    });

    const list = queryClient.getQueryData<Task[]>(['tasks', BRANCH]);
    expect(list?.[0].status).toBe('in_progress');
  });

  // THE OTHER HALF OF THE OWNER'S SENTENCE - "while CREATE works". This is the behaviour the fix
  // above brings UPDATE into line with, pinned so that a later change cannot quietly take it away
  // and leave only one of the two paths optimistic.
  it('still inserts a created task into the list before the round trip finishes', async () => {
    queryClient.setQueryData<Task[]>(['tasks', BRANCH], []);
    vi.mocked(createTask).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useTaskMutations(), { wrapper });

    await act(async () => {
      void result.current.createTaskAsync({ title: 'new task', git_branch_id: BRANCH, status: 'todo' });
    });

    const list = queryClient.getQueryData<Task[]>(['tasks', BRANCH]);
    expect(list?.some(t => t.title === 'new task')).toBe(true);
  });
});
