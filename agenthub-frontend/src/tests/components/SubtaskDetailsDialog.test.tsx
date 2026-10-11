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

describe('SubtaskDetailsDialog: no progress-history surface (O1c)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Shaped the way the subtask read serves it: `details` carries the subtask's own joined progress
  // history - the "=== Progress N ===\n<content>" blocks joined by a blank line - and
  // `progress_history` / `progress_count` are ABSENT, because the subtask DTO serves neither.
  const servedWithHistory = {
    id: subtaskId,
    title: 'Subtask with progress',
    status: 'in_progress',
    details: '=== Progress 1 ===\nFirst subtask note\n\n=== Progress 2 ===\nSecond subtask note',
  } as unknown as Subtask;

  it('shows no progress-history block even when the served subtask carries `details`', async () => {
    // The O1c ruling: progress is events, the ledger timeline is the single progress surface, and the
    // two never coexist. Until the subtask's own `details` are served this dialog shows NO progress
    // history at all (06410692 owns that), so a served `details` must not put the deleted surface
    // back on screen. The progress section is open by default here, which is what makes this case
    // able to fail: a block rendered inside it would be found.
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

    expect(await screen.findByText('Basic Information')).toBeInTheDocument();
    expect(screen.queryByText('Progress History:')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Progress History/ })).not.toBeInTheDocument();
  });
});
