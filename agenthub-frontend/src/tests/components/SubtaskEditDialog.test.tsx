/**
 * @fileoverview SubtaskEditDialog effects depend on `open` and `subtask` only:
 * the form is pre-filled and the seat list is loaded when the dialog opens.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import SubtaskEditDialog from '../../components/SubtaskEditDialog';
import { getAvailableAgents } from '../../api';
import type { Subtask } from '../../api';

vi.mock('../../api', () => ({
  getAvailableAgents: vi.fn(),
}));

vi.mock('../../hooks/useSubtasks', () => ({
  useSubtaskMutations: () => ({
    updateSubtaskAsync: vi.fn(),
    isUpdating: false,
    updateError: null,
  }),
}));

vi.mock('../../components/AgentAssignmentDialog', () => ({
  default: ({ availableSeats, availableSeatsError }: {
    availableSeats: string[];
    availableSeatsError: boolean;
  }) => (
    <div
      data-testid="assignment"
      data-seats={availableSeats.join(',')}
      data-error={String(availableSeatsError)}
    />
  ),
}));

const subtask = (overrides: Partial<Subtask> = {}): Subtask =>
  ({
    id: 'sub-1',
    title: 'Write tests',
    description: 'cover the dialog',
    status: 'todo',
    priority: 'medium',
    assignees: [],
    ...overrides,
  }) as Subtask;

const renderDialog = (open: boolean, current: Subtask) => (
  <SubtaskEditDialog open={open} onOpenChange={vi.fn()} subtask={current} onClose={vi.fn()} />
);

const titleInput = () => screen.getByPlaceholderText('Enter subtask title...') as HTMLInputElement;

describe('SubtaskEditDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAvailableAgents).mockResolvedValue([]);
  });

  it('loads the seat list when it opens and not while it is closed', async () => {
    const { rerender } = render(renderDialog(false, subtask()));
    expect(getAvailableAgents).not.toHaveBeenCalled();

    rerender(renderDialog(true, subtask()));

    await waitFor(() => expect(getAvailableAgents).toHaveBeenCalledTimes(1));
  });

  it('does not reload the seat list when the subtask changes while open', async () => {
    const { rerender } = render(renderDialog(true, subtask()));
    await waitFor(() => expect(getAvailableAgents).toHaveBeenCalledTimes(1));

    rerender(renderDialog(true, subtask({ id: 'sub-2', title: 'Other' })));

    expect(getAvailableAgents).toHaveBeenCalledTimes(1);
  });

  it('pre-fills the form from the subtask when it opens', async () => {
    const { rerender } = render(renderDialog(false, subtask({ title: 'Opened title' })));

    rerender(renderDialog(true, subtask({ title: 'Opened title' })));

    expect(titleInput().value).toBe('Opened title');
    await waitFor(() => expect(getAvailableAgents).toHaveBeenCalled());
  });

  it('pre-fills again when the subtask changes while open', async () => {
    const { rerender } = render(renderDialog(true, subtask()));
    expect(titleInput().value).toBe('Write tests');

    rerender(renderDialog(true, subtask({ id: 'sub-2', title: 'Other subtask' })));

    expect(titleInput().value).toBe('Other subtask');
    await waitFor(() => expect(getAvailableAgents).toHaveBeenCalled());
  });

  it('discards unsaved edits when it is closed and opened again', async () => {
    const current = subtask();
    const { rerender } = render(renderDialog(true, current));
    fireEvent.change(titleInput(), { target: { value: 'Unsaved edit' } });
    expect(titleInput().value).toBe('Unsaved edit');

    rerender(renderDialog(false, current));
    rerender(renderDialog(true, current));

    expect(titleInput().value).toBe('Write tests');
    await waitFor(() => expect(getAvailableAgents).toHaveBeenCalledTimes(2));
  });

  describe('seat load', () => {
    it('hands the seats to the assignment dialog without an error', async () => {
      vi.mocked(getAvailableAgents).mockResolvedValue(['@lead']);

      render(renderDialog(true, subtask()));

      await waitFor(() => expect(screen.getByTestId('assignment')).toHaveAttribute('data-seats', '@lead'));
      expect(screen.getByTestId('assignment')).toHaveAttribute('data-error', 'false');
    });

    it('flags a failed seat load', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.mocked(getAvailableAgents).mockRejectedValue(new Error('seat API down'));

      render(renderDialog(true, subtask()));

      await waitFor(() => expect(screen.getByTestId('assignment')).toHaveAttribute('data-error', 'true'));
      expect(screen.getByTestId('assignment')).toHaveAttribute('data-seats', '');
    });
  });
});
