/**
 * @fileoverview SubtaskDetailsDialog — the JSON tab's FILE NAME is built from the subtask id.
 *
 * The id comes from a producer the type does not bind: a fetch that omits the key yields a truthy
 * object whose `id` is undefined, and `fullSubtask.id.slice(0, 8)` then throws DURING RENDER, which
 * takes the dialog - and the page under it - down. This file exists because that site had no test
 * and no guard, while its sibling in the seat panel got both (`cd163bb7`).
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
