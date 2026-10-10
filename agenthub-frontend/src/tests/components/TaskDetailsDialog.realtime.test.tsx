// The owner's report, on the DETAIL surface: a task status changes and an OPEN
// TaskDetailsDialog keeps showing the old one.
//
// The layer that refuses the frame is GO (it is stamped userId 'system' and the delivery gate
// fails closed), so this file pins the CLIENT half: once a frame DOES arrive, does the open
// dialog show what it carried? Before this file's fix the answer was no - the dialog rendered a
// local snapshot and only a reopen refreshed it, while useRealtimeSync wrote the frame into
// ['task', taskId, false] where nothing was reading.
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect } from 'vitest';
import * as api from '../../api';
import type { Task } from '../../types/api.types';
import type { WSMessage } from '../../types/websocket-protocol';
import TaskDetailsDialog from '../../components/TaskDetailsDialog';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';

vi.mock('../../api', () => ({
  // Everything useTasks.ts imports, so the mocked module links the same way the real one does.
  getTask: vi.fn(),
  getTaskContext: vi.fn(),
  getCurrentUserId: vi.fn(() => 'mock-user-id'),
  getTasks: vi.fn(),
  updateTask: vi.fn(),
  createTask: vi.fn(),
  deleteTask: vi.fn(),
  completeTask: vi.fn(),
}));

vi.mock('js-cookie', () => ({
  default: { get: vi.fn(() => 'mock-token'), remove: vi.fn() },
}));

vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: vi.fn(() => vi.fn()),
  useInfoToast: vi.fn(() => vi.fn()),
  useWarningToast: vi.fn(() => vi.fn()),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

vi.mock('../../utils/contextHelpers', () => ({
  formatContextDisplay: vi.fn(() => ({
    hasInfo: false,
    completionSummary: null,
    completionPercentage: null,
    taskStatus: null,
    testingNotes: [],
    isLegacy: false,
  })),
}));

vi.mock('../../components/ClickableAssignees', () => ({
  __esModule: true,
  default: ({ assignees }: any) => (
    <div data-testid="clickable-assignees">{(assignees ?? []).join(',')}</div>
  ),
}));
vi.mock('../../components/ProgressHistoryTimeline', () => ({ ProgressHistoryTimeline: () => <div /> }));
vi.mock('../../components/ui/CopyableId', () => ({ CopyableId: ({ id }: any) => <span>{id}</span> }));
vi.mock('../../components/ui/RawJSONDisplay', () => ({ __esModule: true, default: () => <div /> }));
vi.mock('../../components/ui/EnhancedJSONViewer', () => ({ EnhancedJSONViewer: () => <div /> }));

describe('TaskDetailsDialog - an OPEN dialog takes an arriving status change', () => {
  it('renders the status the realtime frame carried, on the key useRealtimeSync writes', async () => {
    const TASK_ID = 'task-123';
    const SERVER_STATUS = 'todo';
    const FRAME_STATUS = 'in_progress';

    // The server answers the SAME status for the whole test, so the only possible source of
    // FRAME_STATUS in the UI is the frame's cache write. A refetch cannot fake a pass.
    const serverTask = {
      id: TASK_ID,
      title: 'Surface Task',
      description: '',
      status: SERVER_STATUS,
      priority: 'high',
      git_branch_id: 'branch-123',
      project_id: 'project-123',
      assignees: [],
      labels: [],
      created_at: '2026-10-09T18:00:00Z',
      updated_at: '2026-10-09T18:00:00Z',
    } as unknown as Task;

    (api.getTask as any).mockResolvedValue(serverTask);
    (api.getTaskContext as any).mockResolvedValue(null);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    // FIELD FOR FIELD the frame agenthub_go's BroadcastDataChange builds for a task update:
    // payload.data.primary is the task dict, metadata.source is 'user' for an update, and
    // metadata.userId is the literal 'system' the facade stamps.
    const frame = {
      id: 'broadcast-task-1',
      version: '2.0',
      type: 'update',
      timestamp: '2026-10-09T20:00:00Z',
      sequence: 7,
      payload: { entity: 'task', action: 'updated', data: { primary: { ...serverTask, status: FRAME_STATUS } } },
      metadata: {
        source: 'user',
        userId: 'system',
        entity_type: 'task',
        entity_id: TASK_ID,
        event_type: 'updated',
      },
    } as unknown as WSMessage;

    const mockWs = {
      on: vi.fn((event: string, handler: (m: WSMessage) => void) => {
        if (event === 'update') {
          setTimeout(() => handler(frame), 20);
        }
      }),
      off: vi.fn(),
    };

    // The production arrangement: one QueryClient, useRealtimeSync mounted beside the dialog.
    const Host = () => {
      useRealtimeSync(mockWs, true);
      return null;
    };

    render(
      <>
        <Host />
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={serverTask}
          onClose={() => {}}
          onAgentClick={() => {}}
        />
      </>,
      { wrapper }
    );

    await waitFor(() => expect(screen.getByText('Surface Task')).toBeInTheDocument());
    expect(screen.getByText(/Status: todo/i)).toBeInTheDocument();

    // The frame arrived: the write is observable on the real key (and is the only writer here).
    await waitFor(
      () => expect(queryClient.getQueryData<Task>(['task', TASK_ID, false])?.status).toBe(FRAME_STATUS),
      { timeout: 2000 }
    );

    // The open dialog shows it, without a reopen.
    await waitFor(
      () => expect(screen.getByText(/Status: in progress/i)).toBeInTheDocument(),
      { timeout: 2000 }
    );
  });
});
