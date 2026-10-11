/**
 * The task dialog's progress surface is the EXECUTION LEDGER, driven here from the payload the API
 * actually serves.
 *
 * WHY THE OLD SUBJECT IS GONE (O1c): this file used to assert that the dialog rendered a
 * progress-history timeline from `details`, the joined history text. The O1c ruling deleted that
 * timeline - progress is events, the ledger timeline is the single progress surface, and the two
 * never coexist - so the question a user can still ask is the one this file asks now: a progress
 * NOTE reaches the dialog's screen as its own text. A row reading only "Progress reported" is the
 * failure mode, because it hides the note the event exists to carry.
 *
 * The 4a0a8c7a lesson still stands and is why nothing here supplies a substituted field: a fake that
 * supplies the input cannot detect its absence, which is exactly how the older suite stayed green
 * while users stopped seeing any progress at all.
 *
 * WHAT THIS FILE STILL CANNOT SEE, recorded rather than left implicit (the 88ab4230 gate's MINOR 1):
 * the payload and the events below are SHAPED BY HAND, so no assertion here can fail when the SERVER
 * changes. The real serialization is not reachable from a vitest case - this suite mocks `../../api`,
 * no test in the tree drives a live server, and there is no checked-in fixture produced by the Go
 * serializer. What WOULD reach it, named so the gap is not silent: (a) a Go test that marshals the
 * real DTO - `task_response.go` builds `Details` from the task's joined history and sets it, and the
 * ledger's own writer emits the progress event's `{ content, progress_number }`; that test belongs
 * with the producer, in agenthub_go; or (b) an end-to-end case against the deployed API, which is
 * the only place the served bytes exist.
 */
import { render, screen, waitFor } from './../test-utils';
import React from 'react';
import { vi } from 'vitest';
import * as api from '../../api';
import { Task } from '../../api';
import type { TaskEventsResponse } from '../../types/taskTypes';
import TaskDetailsDialog from '../../components/TaskDetailsDialog';

vi.mock('../../api', () => ({
  getTask: vi.fn(),
  getTaskEvents: vi.fn(),
  getTaskContext: vi.fn(),
  getCurrentUserId: vi.fn(() => 'mock-user-id')
}));

vi.mock('../../utils/contextHelpers', () => ({
  formatContextDisplay: vi.fn(() => ({
    hasInfo: false,
    completionSummary: null,
    completionPercentage: null,
    taskStatus: null,
    testingNotes: [],
    isLegacy: false
  }))
}));

vi.mock('js-cookie', () => ({
  default: { get: vi.fn(() => 'mock-token'), remove: vi.fn() }
}));

vi.mock('../../components/ClickableAssignees', () => ({
  __esModule: true,
  default: ({ assignees }: any) => <div data-testid="clickable-assignees">{assignees?.join(', ')}</div>
}));

vi.mock('../../components/ui/CopyableId', () => ({
  CopyableId: ({ id }: any) => <span>{id}</span>
}));

vi.mock('../../components/ui/RawJSONDisplay', () => ({
  __esModule: true,
  default: () => <div data-testid="raw-json-display" />
}));

vi.mock('../../components/ui/EnhancedJSONViewer', () => ({
  EnhancedJSONViewer: () => <div data-testid="enhanced-json-viewer" />
}));

describe('TaskDetailsDialog: the ledger is the progress surface', () => {
  // Shaped the way the Go DTO serves a task since 4a0a8c7a: `details` carries the joined progress
  // history - the "=== Progress N ===\n<content>" blocks Task.AppendProgress writes, joined by a
  // blank line - and the two dropped fields are ABSENT, not empty, because that is what the payload
  // does now.
  const servedPayload = {
    id: 'task-progress-1',
    title: 'Task with progress',
    description: 'desc',
    status: 'in_progress',
    priority: 'high',
    git_branch_id: 'branch-1',
    project_id: 'project-1',
    created_at: '2025-08-27T10:00:00Z',
    updated_at: '2025-08-27T11:00:00Z',
    assignees: [],
    labels: [],
    dependencies: [],
    subtasks: [],
    details: '=== Progress 1 ===\nFirst progress note\n\n=== Progress 2 ===\nSecond progress note',
    progress_percentage: 40
  } as unknown as Task;

  // The real progress event the ledger writes for a note: the text and the number it was given.
  const servedEvents: TaskEventsResponse = {
    success: true,
    events: [
      {
        id: 'event-1',
        task_id: 'task-progress-1',
        seq: 1,
        kind: 'progress',
        actor_kind: 'seat',
        actor_id: 'dev/fe-dev',
        payload: { content: '=== Progress 1 ===\nFirst progress note', progress_number: 1 },
        created_at: '2025-08-27T10:05:00Z'
      }
    ],
    count: 1,
    after_seq: 0
  };

  it('renders a note from the ledger as its own text, with the ledger as the only progress surface', async () => {
    vi.mocked(api.getTask).mockResolvedValue(servedPayload);
    vi.mocked(api.getTaskEvents).mockResolvedValue(servedEvents);
    vi.mocked(api.getTaskContext).mockResolvedValue({ data: {} });

    render(
      <TaskDetailsDialog
        open={true}
        onOpenChange={() => {}}
        task={servedPayload}
        onClose={() => {}}
        onAgentClick={() => {}}
      />
    );

    await waitFor(() => expect(screen.getByText('Task with progress')).toBeInTheDocument());

    // The note is on screen because the EVENT carried it, and the numbered header the column adds is
    // stripped: the timeline shows the note, not the column's formatting.
    expect(await screen.findByText('First progress note')).toBeInTheDocument();
    expect(screen.queryByText(/=== Progress 1 ===/)).not.toBeInTheDocument();

    // ONE progress surface, and it is the ledger's own: the phase badge can only come from the events.
    expect(screen.getByLabelText(/Ledger phase:/)).toBeInTheDocument();
  });
});
