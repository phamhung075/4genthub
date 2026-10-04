/**
 * @fileoverview The seat list of the assignment dialog tells a failed load, a user
 * without seats and a search without a match apart.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import AgentAssignmentDialog from '../../components/AgentAssignmentDialog';

const renderDialog = (props: { availableAgents: string[]; availableAgentsError?: boolean }) =>
  render(
    <AgentAssignmentDialog
      open={true}
      onOpenChange={vi.fn()}
      task={null}
      onClose={vi.fn()}
      onAssign={vi.fn()}
      agents={[]}
      {...props}
    />
  );

describe('AgentAssignmentDialog seat list', () => {
  it('lists the seats with a count', () => {
    renderDialog({ availableAgents: ['@lead', '@go-dev'] });

    expect(screen.getByText('Seats (2)')).toBeInTheDocument();
    expect(screen.getByText('@lead')).toBeInTheDocument();
    expect(screen.getByText('@go-dev')).toBeInTheDocument();
  });

  it('points a user without seats to the Seats page', () => {
    renderDialog({ availableAgents: [] });

    expect(screen.getByText('You have no seats yet. Seats are created on the Seats page.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('reports a failed load as an error, not as an empty list', () => {
    renderDialog({ availableAgents: [], availableAgentsError: true });

    expect(screen.getByRole('alert')).toHaveTextContent('Could not load your seats');
    expect(screen.queryByText(/no seats yet/i)).not.toBeInTheDocument();
  });

  it('says so when a search matches no seat', () => {
    renderDialog({ availableAgents: ['@lead'] });

    fireEvent.change(screen.getByPlaceholderText('Search seats...'), { target: { value: 'zzz' } });

    expect(screen.getByText('No seats found matching "zzz"')).toBeInTheDocument();
  });
});
