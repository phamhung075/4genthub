/**
 * @fileoverview SubtaskDetailsDialog — the JSON tab's FILE NAME is built from the subtask id, and
 * the Progress block's TIMELINE is built from the SERVED `details` text.
 *
 * THE FILE NAME: the id comes from a producer the type does not bind: a fetch that omits the key
 * yields a truthy object whose `id` is undefined, and `fullSubtask.id.slice(0, 8)` then throws
 * DURING RENDER, which takes the dialog - and the page under it - down. This file exists because
 * that site had no test and no guard, while its sibling in the seat panel got both (`cd163bb7`).
 *
 * THE TIMELINE: `06410692` gave `SubtaskDTO` a `Details` field filled from the subtask's OWN joined
 * progress history (`types/converters.go`'s `subtaskDetails` -> `entities.ProgressHistoryText`), and
 * this dialog reads it as `fullSubtask.details` under a presence guard. Until that commit the read
 * was pointed at a field nothing served, so the block could only ever stay hidden; the two cases at
 * the bottom of this file are the ones that now discriminate: rendered when the field arrives, and
 * hidden - not an empty labelled block - when it does not.
 */

import React from 'react';
import { render, screen, fireEvent } from '../test-utils';
import { vi } from 'vitest';
import { SubtaskDetailsDialog } from '../../components/SubtaskDetailsDialog';
import { getSubtask, type Subtask } from '../../api';

vi.mock('../../api');

const subtaskId = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';

const subtask = { id: subtaskId, title: 'Subtask 1', status: 'todo' } as unknown as Subtask;

describe('SubtaskDetailsDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the JSON tab when the fetched subtask carries no id', async () => {
    // The producer's absence rather than the type's: no `id` key at all, so the file name cannot be
    // built from it. Before the guard this threw "Cannot read properties of undefined (reading
    // 'slice')" as soon as the JSON tab rendered.
    vi.mocked(getSubtask).mockResolvedValue({
      title: 'Subtask 1',
      status: 'todo',
    } as unknown as Subtask);

    render(
      <SubtaskDetailsDialog
        open
        onOpenChange={vi.fn()}
        subtask={subtask}
        parentTaskId="task-123"
        onClose={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /json/i }));

    // The dialog survives and shows its JSON view rather than unmounting the page.
    expect(await screen.findByText(/View Complete Raw Subtask Data/i)).toBeInTheDocument();
  });
});

describe('SubtaskDetailsDialog: the served `details` drives the progress timeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Shaped the way the subtask read serves it since `06410692`: `details` carries the subtask's own
  // joined progress history - the "=== Progress N ===\n<content>" blocks joined by a blank line -
  // and `progress_history` / `progress_count` are ABSENT, because the subtask DTO serves neither.
  const servedWithHistory = {
    id: subtaskId,
    title: 'Subtask with progress',
    status: 'in_progress',
    details: '=== Progress 1 ===\nFirst subtask note\n\n=== Progress 2 ===\nSecond subtask note',
  } as unknown as Subtask;

  it('renders the timeline with its count from the SERVED text when details is present', async () => {
    vi.mocked(getSubtask).mockResolvedValue(servedWithHistory);

    render(
      <SubtaskDetailsDialog
        open
        onOpenChange={vi.fn()}
        subtask={subtask}
        parentTaskId="task-123"
        onClose={vi.fn()}
      />
    );

    // The dialog's own label for the block, then the REAL compact timeline under it: the trigger
    // carries the count derived from the served text itself, because `progress_count` is not served.
    expect(await screen.findByText('Progress History:')).toBeInTheDocument();
    const trigger = screen.getByRole('button', { name: /Progress History/ });
    expect(trigger.textContent).toContain('2');

    // The entries are what the served text parses into, not a substituted value. The compact
    // timeline starts collapsed, so expanding it is what puts them on screen.
    fireEvent.click(trigger);
    expect(await screen.findByText('First subtask note')).toBeInTheDocument();
    expect(screen.getByText('Second subtask note')).toBeInTheDocument();
  });

  it('stays hidden rather than crashing or rendering an empty labelled block when details is absent', async () => {
    // A subtask with no history at all: `SubtaskDTO.Details` is nil, which is the shape the guard
    // exists for rather than a payload we expect in practice.
    vi.mocked(getSubtask).mockResolvedValue({
      id: subtaskId,
      title: 'Subtask without history',
      status: 'todo',
    } as unknown as Subtask);

    render(
      <SubtaskDetailsDialog
        open
        onOpenChange={vi.fn()}
        subtask={subtask}
        parentTaskId="task-123"
        onClose={vi.fn()}
      />
    );

    // The dialog rendered its details tab, so the absent field did not take it down ...
    expect(await screen.findByText('Basic Information')).toBeInTheDocument();
    // ... and the progress block is absent ENTIRELY, not present as an empty label over a null
    // timeline. An unguarded read renders `Progress History:` with nothing under it, which is the
    // state this case fails on.
    expect(screen.queryByText('Progress History:')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Progress History/ })).not.toBeInTheDocument();
  });
});
