/**
 * The 4a0a8c7a regression test: the served payload no longer carries progress_history or
 * progress_count, so the dialog has to render the progress timeline from the field the API
 * actually sends - `details`, the joined history text.
 *
 * This file deliberately does NOT mock ProgressHistoryTimeline, and that is the point of it.
 * The finding on 4a0a8c7a was exactly this: a fake that supplies the field cannot detect its
 * absence. The older suite mocked this component AND built its own payload, so it stayed green
 * after the API stopped sending the two fields while users stopped seeing the timeline at all.
 *
 * WHAT THIS FILE STILL CANNOT SEE, recorded rather than left implicit (the 88ab4230 gate's MINOR 1):
 * the payload below is SHAPED BY HAND, so no assertion here can fail when the SERVER changes. The
 * real serialization is not reachable from a vitest case - this suite mocks `../../api`, no test in
 * the tree drives a live server, and there is no checked-in fixture produced by the Go serializer.
 * What WOULD reach it, named so the gap is not silent: (a) a Go test that marshals the real DTO -
 * `task_response.go:140` builds `Details` from the task's joined history and `:196` sets it
 * (`m.Set("details", r.Details)`) - and asserts `details` present while `progress_history` /
 * `progress_count` are absent; that test belongs with the producer, in agenthub_go; or (b) an
 * end-to-end case against the deployed API, which is the only place the served bytes exist.
 * FALSIFICATION, so a reader can check the claim: this case fails if the server stops sending
 * `details` (the 4a0a8c7a class) or changes the join so the text stops parsing into
 * `=== Progress N ===` blocks - but only once the payload comes from (a) or (b) instead of the
 * object below.
 */
import { render, screen, waitFor } from './../test-utils';
import React from 'react';
import { vi } from 'vitest';
import * as api from '../../api';
import { Task } from '../../api';
import TaskDetailsDialog from '../../components/TaskDetailsDialog';

vi.mock('../../api', () => ({
  getTask: vi.fn(),
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

describe('TaskDetailsDialog: the progress timeline renders from the SERVED payload', () => {
  // Shaped the way the Go DTO serializes a task since 4a0a8c7a: `details` carries the joined
  // progress history - the entries' "=== Progress N ===\n<content>" blocks that
  // Task.AppendProgress writes, joined by a blank line - and the two dropped fields are ABSENT,
  // not empty, because that is what the payload does now.
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

  it('renders the entries and their count with progress_history and progress_count absent', async () => {
    (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(servedPayload);
    (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

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

    // The REAL component - its header, its count derived from the served text, and both entries.
    expect(await screen.findByText('Progress History')).toBeInTheDocument();
    expect(screen.getByText(/First progress note/)).toBeInTheDocument();
    expect(screen.getByText(/Second progress note/)).toBeInTheDocument();

    // The count the badge shows comes from the entries the served text parses into; before the
    // re-point it defaulted to 0, so a "2" here cannot come from a substituted value.
    const badge = screen.getByText(/entries$/);
    expect(badge.textContent).toContain('2');
  });
});
