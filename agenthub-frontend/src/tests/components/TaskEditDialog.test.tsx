/**
 * @fileoverview The assignee dropdown of TaskEditDialog offers the user's seats and
 * tells a failed load, a user without seats and a search without a match apart.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { TaskEditDialog } from '../../components/TaskEditDialog';
import { getAvailableAgents } from '../../api';

vi.mock('../../api', () => ({
  getAvailableAgents: vi.fn(),
}));

const openDropdown = async () => {
  render(
    <TaskEditDialog open={true} onOpenChange={vi.fn()} task={null} onSave={vi.fn()} onClose={vi.fn()} />
  );
  const search = screen.getByPlaceholderText('Search and select seats...');
  fireEvent.focus(search);
  return search;
};

describe('TaskEditDialog assignee dropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('offers the seats of the user', async () => {
    vi.mocked(getAvailableAgents).mockResolvedValue(['@go-dev', '@lead']);

    await openDropdown();

    expect(await screen.findByText('@lead')).toBeInTheDocument();
    expect(screen.getByText('@go-dev')).toBeInTheDocument();
  });

  it('points a user without seats to the Seats page', async () => {
    vi.mocked(getAvailableAgents).mockResolvedValue([]);

    await openDropdown();

    expect(await screen.findByText('You have no seats yet. Seats are created on the Seats page.')).toBeInTheDocument();
  });

  it('reports a failed load as an error', async () => {
    vi.mocked(getAvailableAgents).mockRejectedValue(new Error('seat API down'));

    await openDropdown();

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Could not load your seats'));
    expect(screen.queryByText(/no seats yet/i)).not.toBeInTheDocument();
  });

  it('says so when a search matches no seat', async () => {
    vi.mocked(getAvailableAgents).mockResolvedValue(['@lead']);

    const search = await openDropdown();
    await screen.findByText('@lead');
    fireEvent.change(search, { target: { value: 'zzz' } });

    expect(screen.getByText('No seats found')).toBeInTheDocument();
  });
});
