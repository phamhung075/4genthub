/**
 * @fileoverview The execution ledger's DERIVED phase and its row labels, as pure functions.
 *
 * These are the rules the timeline's badge rests on, and each case here is a rule the lib's own header
 * claims rather than an echo of the implementation: only `status_changed` carries a status, so only it
 * moves the phase; a payload this build cannot read must not invent a status; and every kind and actor
 * class the vocabulary can carry has a label, so no live value reaches the screen as a raw identifier.
 * The UI's half - that the badge is a fold and not a stored field - is asserted in
 * `src/tests/components/TaskEventTimeline.test.tsx`, which renders the four-step sequence.
 */
import { describe, it, expect } from 'vitest';
import {
  ACTOR_LABELS,
  KIND_LABELS,
  PHASE_LABELS,
  contextChangeDetails,
  deriveLedgerPhase,
  describeEvent,
  labelForKind,
  statusChangedTo,
} from '../../lib/taskTimeline';
import { TASK_EVENT_ACTOR_KINDS, TASK_EVENT_KINDS } from '../../types/taskTypes';
import type { TaskEvent, TaskEventActorKind, TaskEventKind } from '../../types/taskTypes';

const ev = (
  seq: number,
  kind: TaskEventKind,
  payload: Record<string, unknown> | null = null,
  actor_kind: TaskEventActorKind = 'seat',
): TaskEvent => ({
  id: `event-${seq}`,
  task_id: 'task-1',
  seq,
  kind,
  actor_kind,
  actor_id: 'dev/fe-dev',
  payload,
  created_at: `2026-10-10T12:0${seq}:00Z`,
});

describe('deriveLedgerPhase', () => {
  it('is unopened for an empty ledger - silence, not todo', () => {
    expect(deriveLedgerPhase([])).toBe('unopened');
    expect(PHASE_LABELS['unopened']).toBe('No events');
  });

  it('moves only on `status_changed`, never on a kind whose payload defines no status', () => {
    // EVERY OTHER KIND IS PRESENT ON PURPOSE: each says that something HAPPENED - a progress note, a
    // verdict, a handover - and none of them says which phase the task is in, so the fold must take
    // none of them for the phase. `evidence_submitted` carries a `new` on purpose too: a field name that
    // looks like a status on the WRONG kind is exactly what must not be read.
    expect(
      deriveLedgerPhase([
        ev(1, 'progress', { note: 'tests written' }),
        ev(2, 'status_changed', { old: 'todo', new: 'in_progress' }),
        ev(3, 'evidence_submitted', { new: 'done' }),
        ev(4, 'gate_verdict', { verdict: 'ACCEPT' }),
        ev(5, 'handover'),
        ev(6, 'context_updated'),
      ]),
    ).toBe('in_progress');
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
    // A `new` on a kind that does not carry a status is not a status change.
    expect(statusChangedTo(ev(1, 'progress', { new: 'done' }))).toBeNull();
  });
});

describe('describeEvent', () => {
  it('names the transition when the payload defines one', () => {
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo', new: 'in_progress' }))).toBe(
      'Status: Todo to In progress',
    );
    // No readable `old`: a new status is still worth naming, and that is all the row can say.
    expect(describeEvent(ev(1, 'status_changed', { new: 'review' }))).toBe('Status: Review');
    // Unreadable in both directions: the row falls back to the kind's own label rather than to nothing.
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo' }))).toBe('Status changed');
  });

  it("shows a progress note's own text rather than the kind label, header stripped", () => {
    // The real payload the ledger writes for a progress event (O1c): the note's text and the number it
    // was given. A row that read only the kind would show every note as "Progress reported", which is
    // the failure this case exists against.
    expect(describeEvent(ev(1, 'progress', { content: 'two cases written', progress_number: 1 }))).toBe(
      'two cases written',
    );
    // The column's own text carries the numbered header; the timeline already shows the order that
    // header was counting, so the row strips it the same way the progress summaries do.
    expect(
      describeEvent(ev(2, 'progress', { content: '=== Progress 2 ===\nSecond note', progress_number: 2 })),
    ).toBe('Second note');
    // A progress event whose payload carries no readable text still names its kind rather than
    // rendering an empty row.
    expect(describeEvent(ev(3, 'progress', { progress_number: 3 }))).toBe('Progress reported');
  });

  it('labels the non-status kinds in words rather than with the kind itself', () => {
    expect(describeEvent(ev(1, 'progress'))).toBe('Progress reported');
    expect(describeEvent(ev(1, 'evidence_submitted'))).toBe('Evidence submitted');
    expect(describeEvent(ev(1, 'gate_verdict'))).toBe('Gate verdict');
    expect(describeEvent(ev(1, 'handover'))).toBe('Handover');
    expect(describeEvent(ev(1, 'context_updated'))).toBe('Context updated');
  });

  it('names every changed path and op a context write recorded, and reports what the cap left out', () => {
    // The payload since `4cf7e9b8` (`ContextUpdatePayload`): the level and version, and the bounded
    // change set. A row that read only the level said nothing about what changed, which is the defect
    // this case exists against.
    const write = (changes: unknown, changes_truncated = 0) => ({
      level: 'task',
      id: 'uuid-1',
      version: 7,
      origin: 'update_context',
      changes,
      changes_truncated,
    });
    expect(
      describeEvent(ev(1, 'context_updated', write([{ path: 'status', op: 'set', old: 'todo', new: 'in_progress' }]))),
    ).toBe('Context updated: set status');
    expect(
      describeEvent(
        ev(2, 'context_updated', write([
          { path: 'implementation_notes.progress_updates', op: 'set', old: 'a', new: 'b' },
          { path: 'insights', op: 'add', new: 'x' },
          { path: 'settings.obsolete', op: 'remove', old: 'y' },
        ])),
      ),
    ).toBe('Context updated: set implementation_notes.progress_updates, add insights, remove settings.obsolete');
    // The cap: the row says how many changes it is NOT showing rather than reading as the whole diff.
    expect(
      describeEvent(ev(3, 'context_updated', write([{ path: 'status', op: 'set', old: 'a', new: 'b' }], 2))),
    ).toBe('Context updated: set status, and 2 more');
    // A payload with no usable change set names no change: the row has nothing to say, and the
    // timeline does not list it (asserted in `TaskEventTimeline.test.tsx`).
    expect(describeEvent(ev(4, 'context_updated', write([])))).toBe('Context updated');
    expect(describeEvent(ev(5, 'context_updated', write([{ path: '', op: 'set' }, { path: 'status' }, 7])))).toBe(
      'Context updated',
    );
    expect(describeEvent(ev(6, 'context_updated', { level: 'task', version: 3 }))).toBe('Context updated');
    expect(describeEvent(ev(7, 'context_updated'))).toBe('Context updated');
  });

  it('shows each changed value on each side, one line per change', () => {
    expect(
      contextChangeDetails(
        ev(1, 'context_updated', {
          level: 'task',
          version: 7,
          changes: [
            { path: 'status', op: 'set', old: 'todo', new: 'in_progress' },
            { path: 'insights', op: 'add', new: 'a\nb' },
            { path: 'settings.obsolete', op: 'remove', old: { keep: false } },
            { path: 'notes', op: 'set', old: 'short', new: { truncated: true, bytes: 900, sha256: 'abcdef0123456789' } },
          ],
        }),
      ),
    ).toEqual([
      'at task context, version 7',
      'status: todo to in_progress',
      'insights: a b added',
      'settings.obsolete: {"keep":false} removed',
      'notes: short to 900 bytes (sha256 abcdef012345...)',
    ]);
    // A write with no readable change set has no detail lines, and neither has any other kind.
    expect(contextChangeDetails(ev(2, 'context_updated', { level: 'task', changes: [] }))).toEqual([]);
    expect(contextChangeDetails(ev(3, 'progress', { content: 'a note' }))).toEqual([]);
  });

  it('prints a status this build does not know as itself rather than hiding it', () => {
    expect(describeEvent(ev(1, 'status_changed', { old: 'todo', new: 'quarantined' }))).toBe(
      'Status: Todo to quarantined',
    );
  });

  it('prints a KIND this build does not know as itself rather than as nothing', () => {
    // The row is the record: a kind the server adds tomorrow is still what happened.
    expect(labelForKind('planned')).toBe('planned');
  });
});

describe('the label maps cover the whole vocabulary', () => {
  // THE COVERAGE INVARIANT, NOT A COUNT: each case fails when a kind or an actor class has no usable
  // label, and NONE of them reads how many entries a map has - adding a member to the vocabulary is what
  // must break this, not a length that a rename would leave intact.
  it.each(TASK_EVENT_KINDS)('gives the kind %s its own label', (kind) => {
    const label = KIND_LABELS[kind];
    expect(typeof label).toBe('string');
    expect((label ?? '').trim()).not.toBe('');
    expect(label).not.toBe(kind);
  });

  it.each(TASK_EVENT_ACTOR_KINDS)('gives the actor class %s its own label', (actor) => {
    const label = ACTOR_LABELS[actor];
    expect(typeof label).toBe('string');
    expect((label ?? '').trim()).not.toBe('');
    expect(label).not.toBe(actor);
  });
});
