/**
 * @fileoverview The task details view's EXECUTION LEDGER timeline, driven by the REAL event shapes
 * the ledger writes.
 *
 * WHAT THE FOUR-STEP CASE IS, AND WHAT IT CANNOT BE: NEXT_GEN O8's timeline acceptance names a
 * TEST-fail -> FIX -> TEST-pass -> ACCEPT sequence. The ledger's CHECK constraint carries the TWELVE
 * kinds (`ck_task_event_kind`, task_event_tables.go:40), `status_changed` is the only kind any writer
 * emits today, and it is the only kind with a defined payload, `{ old, new }`. So each step is
 * expressed as the nearest real shape and the MAPPING IS REPORTED IN THE CHANGELOG, not dressed up
 * here:
 *
 *   TEST-fail -> status_changed {in_progress -> testing}
 *   FIX       -> status_changed {testing -> in_progress}   (FIX has NO dedicated kind at all)
 *   TEST-pass -> status_changed {in_progress -> review}
 *   ACCEPT    -> status_changed {review -> done}           (`gate_verdict` IS in the vocabulary now
 *                                                           and no writer emits it yet)
 *
 * The distinction the vocabulary CANNOT make YET is that a test failed or passed: `evidence_submitted`
 * is in the vocabulary and has no writer. The component therefore says so on screen
 * (`LEDGER_NOT_RECORDED`) and this file asserts that sentence is present - the forward-looking half
 * is marked NOT IMPLEMENTED rather than claimed by a green case.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test-utils';
import { TaskEventTimeline } from '../../components/TaskEventTimeline';
import { LEDGER_NOT_RECORDED } from '../../lib/taskTimeline';
import type { TaskEvent, TaskEventActorKind, TaskEventKind } from '../../types/taskTypes';

const api = vi.hoisted(() => ({
  getTaskEvents: vi.fn(),
  // The provider stack in test-utils mounts AuthContext, which reads these through ../api.
  getTask: vi.fn(),
  getTaskContext: vi.fn(),
  getCurrentUserId: vi.fn().mockReturnValue('user-1'),
}));

vi.mock('../../api', () => ({
  getTaskEvents: api.getTaskEvents,
  getTask: api.getTask,
  getTaskContext: api.getTaskContext,
  getCurrentUserId: api.getCurrentUserId,
}));

/** Builds a row with the wire's own field names, so the fixture cannot drift from the response. */
const row = (
  seq: number,
  kind: TaskEventKind,
  payload: Record<string, unknown> | null,
  actor_kind: TaskEventActorKind = 'seat',
): TaskEvent => ({
  id: `event-${seq}`,
  task_id: 'task-1',
  seq,
  kind,
  actor_kind,
  actor_id: actor_kind === 'seat' ? 'dev/fe-dev' : 'user-1',
  payload,
  created_at: `2026-10-10T12:0${seq}:00Z`,
});

const body = (events: TaskEvent[]) => ({
  success: true,
  events,
  count: events.length,
  after_seq: 0,
});

const TEST_FAIL = row(1, 'status_changed', { old: 'in_progress', new: 'testing' });
const FIX = row(2, 'status_changed', { old: 'testing', new: 'in_progress' });
const TEST_PASS = row(3, 'status_changed', { old: 'in_progress', new: 'review' });
const ACCEPT = row(4, 'status_changed', { old: 'review', new: 'done' });

const renderTimeline = (events: TaskEvent[]) => {
  api.getTaskEvents.mockResolvedValue(body(events));
  return render(<TaskEventTimeline taskId="task-1" />);
};

describe('TaskEventTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getCurrentUserId.mockReturnValue('user-1');
  });

  it('renders a TEST-fail -> FIX -> TEST-pass -> ACCEPT sequence, each step as the real shape the ledger writes', async () => {
    renderTimeline([TEST_FAIL, FIX, TEST_PASS, ACCEPT]);

    // The four steps, in the order the ledger returns them (seq ascending), each naming the real
    // status transition the ledger can express. FIX is the transition back to in_progress: it has
    // no kind of its own, which is why this row reads as a status move rather than as a fix.
    await waitFor(() => expect(screen.getByText('Status: In progress to Testing')).toBeInTheDocument());
    expect(screen.getByText('Status: Testing to In progress')).toBeInTheDocument();
    expect(screen.getByText('Status: In progress to Review')).toBeInTheDocument();
    expect(screen.getByText('Status: Review to Done')).toBeInTheDocument();

    // Actor class is rendered from the row rather than assumed, as a LABEL and not as the raw value.
    expect(screen.getAllByText(/· a seat/)).toHaveLength(4);
  });

  it('derives the phase from the SEQUENCE, and it tracks the events rather than any stored field', async () => {
    // The component takes no status prop and the ledger body carries no status, so the badge can
    // only come from the events. Two different sequences must therefore give two phases - which is
    // what a stored passthrough could not do.
    const { unmount } = renderTimeline([TEST_FAIL, FIX, TEST_PASS, ACCEPT]);
    await waitFor(() =>
      expect(screen.getByLabelText('Ledger phase: Done')).toBeInTheDocument(),
    );
    unmount();
    vi.clearAllMocks();

    // The same task, stopped at review: ACCEPT has not happened, so the phase must not be Done.
    renderTimeline([TEST_FAIL, FIX, TEST_PASS]);
    await waitFor(() =>
      expect(screen.getByLabelText('Ledger phase: Review')).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Ledger phase: Done')).not.toBeInTheDocument();
  });

  it('marks what the vocabulary cannot record instead of claiming it', async () => {
    renderTimeline([TEST_FAIL, FIX, TEST_PASS, ACCEPT]);

    // The sentence is the honest half: the ledger cannot say a test failed or passed, so the
    // timeline states the limit rather than letting a status move read as a test result.
    await waitFor(() => expect(screen.getByText(LEDGER_NOT_RECORDED)).toBeInTheDocument());
  });

  it('labels every kind in the vocabulary, and never shows the raw class string', async () => {
    // The kinds here are the ones nothing writes YET plus the one that does, and every actor class the
    // CHECK constraint allows except `seat`, which the case above covers.
    renderTimeline([
      row(1, 'assigned', null, 'gate'),
      row(2, 'progress', { note: 'two cases written' }),
      row(3, 'status_changed', { old: 'todo', new: 'in_progress' }),
      row(4, 'gate_verdict', { verdict: 'ACCEPT' }, 'human'),
      row(5, 'handover', null, 'client'),
    ]);

    await waitFor(() => expect(screen.getByText('Assigned')).toBeInTheDocument());
    expect(screen.getByText('Progress reported')).toBeInTheDocument();
    expect(screen.getByText('Status: Todo to In progress')).toBeInTheDocument();
    expect(screen.getByText('Gate verdict')).toBeInTheDocument();
    expect(screen.getByText('Handover')).toBeInTheDocument();

    // THE PHASE DOES NOT MOVE ON ANY OF THEM: only `status_changed` carries a status, so the badge is the
    // one the status change named rather than the last row's kind.
    expect(screen.getByLabelText('Ledger phase: In progress')).toBeInTheDocument();

    // ACTOR CLASS AND KIND ARE BOTH LABELS, never the wire's own value - a raw identifier on screen is
    // exactly what the label maps exist to prevent.
    expect(screen.getByText(/· a gate/)).toBeInTheDocument();
    expect(screen.getByText(/· a person/)).toBeInTheDocument();
    expect(screen.getByText(/· a client/)).toBeInTheDocument();
    expect(screen.queryByText(/· gate /)).not.toBeInTheDocument();
    expect(screen.queryByText('gate_verdict')).not.toBeInTheDocument();
    expect(screen.queryByText('handover')).not.toBeInTheDocument();
  });

  it('reports an empty ledger as silence rather than as todo', async () => {
    renderTimeline([]);

    await waitFor(() =>
      expect(screen.getByText('No ledger events for this task yet.')).toBeInTheDocument(),
    );
    expect(screen.getByLabelText('Ledger phase: No events')).toBeInTheDocument();
  });
});
