/**
 * @fileoverview The execution ledger's DERIVED phase and its row labels, as pure functions.
 *
 * These are the rules the timeline's badge rests on, and each case here is a rule the lib's own
 * header claims rather than an echo of the implementation: `updated` says something changed, not
 * WHICH phase it is; a payload this build cannot read must not invent a status; and terminal kinds
 * say so directly. The UI's half - that the badge is a fold and not a stored field - is asserted in
 * `src/tests/components/TaskEventTimeline.test.tsx`, which renders the four-step sequence.
 */
import { describe, it, expect } from 'vitest';
import {
  LEDGER_NOT_RECORDED,
  PHASE_LABELS,
  deriveLedgerPhase,
  describeEvent,
  statusChangedTo,
} from '../../lib/taskTimeline';
import type { TaskEvent, TaskEventKind } from '../../types/taskTypes';

const ev = (
  seq: number,
  kind: TaskEventKind,
  payload: Record<string, unknown> | null = null,
): TaskEvent => ({
  id: `event-${seq}`,
  task_id: 'task-1',
  seq,
  kind,
  actor_kind: 'agent',
  actor_id: 'fe-dev',
  payload,
  created_at: `2026-10-10T12:0${seq}:00Z`,
});

describe('deriveLedgerPhase', () => {
  it('is unopened for an empty ledger - silence, not todo', () => {
    expect(deriveLedgerPhase([])).toBe('unopened');
    expect(PHASE_LABELS['unopened']).toBe('No events');
  });

  it('does NOT move on `updated`: that kind does not carry which phase the task is in', () => {
    const phase = deriveLedgerPhase([
      ev(1, 'created'),
      ev(2, 'status_changed', { old: 'todo', new: 'in_progress' }),
      ev(3, 'updated'),
    ]);
    expect(phase).toBe('in_progress');
  });

  it('keeps the phase it had when a status_changed payload cannot be read', () => {
    // A payload with no readable `new` is not evidence of a status, so the fold must not invent one
    // - neither on the first event nor after a real transition.
    expect(deriveLedgerPhase([ev(1, 'status_changed', {})])).toBe('unopened');
    expect(deriveLedgerPhase([ev(1, 'status_changed', { new: 'launched' })])).toBe('unopened');
    expect(
      deriveLedgerPhase([
        ev(1, 'status_changed', { old: 'todo', new: 'review' }),
        ev(2, 'status_changed', null),
      ]),
    ).toBe('review');
  });

  it('lets a terminal kind say so directly, and a later status change speak after it', () => {
    expect(deriveLedgerPhase([ev(1, 'created'), ev(2, 'completed')])).toBe('completed');
    expect(deriveLedgerPhase([ev(1, 'created'), ev(2, 'deleted')])).toBe('deleted');
    expect(
      deriveLedgerPhase([ev(1, 'created'), ev(2, 'completed'), ev(3, 'status_changed', { old: 'done', new: 'review' })]),
    ).toBe('review');
  });

  it('folds the four-step acceptance sequence to its last step', () => {
    // TEST-fail -> FIX -> TEST-pass -> ACCEPT, each as the nearest REAL shape the ledger carries.
    expect(
      deriveLedgerPhase([
        ev(1, 'status_changed', { old: 'in_progress', new: 'testing' }),
        ev(2, 'status_changed', { old: 'testing', new: 'in_progress' }),
        ev(3, 'status_changed', { old: 'in_progress', new: 'review' }),
        ev(4, 'status_changed', { old: 'review', new: 'done' }),
      ]),
    ).toBe('done');
  });
});

describe('statusChangedTo', () => {
  it('accepts a status in the vocabulary and rejects one outside it', () => {
    expect(statusChangedTo(ev(1, 'status_changed', { old: 'todo', new: 'blocked' }))).toBe('blocked');
    expect(statusChangedTo(ev(1, 'status_changed', { old: 'todo', new: 'nonsense' }))).toBeNull();
    expect(statusChangedTo(ev(1, 'status_changed', { old: 'todo' }))).toBeNull();
    expect(statusChangedTo(ev(1, 'updated', { new: 'done' }))).toBeNull();
  });
});

describe('describeEvent', () => {
  it('names the transition when the payload defines one and the kind otherwise', () => {
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo', new: 'in_progress' }))).toBe(
      'Status: Todo to In progress',
    );
    // No readable `old`: a new status is still worth naming, and that is all the row can say.
    expect(describeEvent(ev(1, 'status_changed', { new: 'review' }))).toBe('Status: Review');
    // Unreadable in both directions: the row says what it knows, which is that something moved.
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo' }))).toBe('Status changed');
    expect(describeEvent(ev(1, 'created'))).toBe('Created');
    expect(describeEvent(ev(1, 'updated'))).toBe('Updated');
    expect(describeEvent(ev(1, 'completed'))).toBe('Completed');
    expect(describeEvent(ev(1, 'deleted'))).toBe('Deleted');
  });

  it('prints a status this build does not know as itself rather than hiding it', () => {
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo', new: 'quarantined' }))).toBe(
      'Status: Todo to quarantined',
    );
  });

  it('prints the limit of the vocabulary as a sentence a reader can act on', () => {
    expect(LEDGER_NOT_RECORDED).toContain('not in the event vocabulary yet');
    expect(LEDGER_NOT_RECORDED).toContain('not that its tests passed');
  });
});
