/**
 * @fileoverview RoomSharingDialog: the owner sets or clears a room's team, a viewer is told why they
 * cannot, and a refusal is shown in the server's own words.
 *
 * WHAT IS PINNED IS THE GATE. `PUT /rooms/{room}/team` is owner-only on the wire (`seatAdminRoom`
 * resolves the room through `GetRoomBySlug(userID, slug)`, which returns the caller's own room only),
 * and `GET /rooms` hands the caller rooms they do NOT own as well - so the panel must take the
 * standing from the room body's `role` rather than infer it. A viewer case asserts NO control is
 * rendered, which is the half a permissive default would silently break.
 *
 * The clear case is separate from the set case because an empty team is a VALUE the route acts on
 * (the room becomes private again), not an absence the form might drop: the assertion is that the
 * mutation receives the empty string, not that the button merely became enabled.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { RoomSharingDialog } from '../../components/seats/RoomSharingDialog';
import type { Room, TeamMembership } from '../../types/seatTypes';

// vi.mock is hoisted above the module body, so the state the factory closes over must be hoisted too.
const mocks = vi.hoisted(() => ({
  teams: [] as TeamMembership[],
  mutate: (() => {}) as unknown as (team: string, options?: { onSuccess?: () => void }) => void,
  isPending: false,
  isError: false,
  error: null as Error | null,
}));

vi.mock('../../hooks/useSeats', () => ({
  useTeams: () => ({ teams: mocks.teams, isLoading: false, error: null }),
  useSetRoomTeam: () => ({
    mutate: mocks.mutate,
    isPending: mocks.isPending,
    isError: mocks.isError,
    error: mocks.error,
    reset: () => {},
  }),
}));

const membership = (id: string, slug: string, name: string): TeamMembership => ({
  team: { id, slug, name, owner_user_id: 'owner-user' },
  role: 'owner',
});

const memberships = [membership('team-eng', 'eng', 'Engineering'), membership('team-ops', 'ops', 'Ops')];

const room = (overrides: Partial<Room> = {}): Room => ({
  id: 'room-dev',
  slug: 'dev',
  name: 'Dev',
  team_id: '',
  role: 'owner',
  ...overrides,
});

beforeEach(() => {
  mocks.teams = memberships;
  mocks.mutate = vi.fn();
  mocks.isPending = false;
  mocks.isError = false;
  mocks.error = null;
});

describe('RoomSharingDialog', () => {
  it('offers the owner the caller teams and sends the chosen slug', () => {
    render(<RoomSharingDialog room={room()} onClose={() => {}} />);

    const select = screen.getByLabelText('Shared with') as HTMLSelectElement;
    expect(select.value).toBe('');
    expect(screen.getByRole('option', { name: 'Private - only you' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Engineering (eng)' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Ops (ops)' })).toBeTruthy();

    const save = screen.getByRole('button', { name: /Save sharing/ }) as HTMLButtonElement;
    // The room is private and nothing has been chosen: saving an unchanged value is not offered.
    expect(save.disabled).toBe(true);

    fireEvent.change(select, { target: { value: 'eng' } });
    expect(save.disabled).toBe(false);
    fireEvent.click(save);

    expect(mocks.mutate).toHaveBeenCalledTimes(1);
    expect(mocks.mutate.mock.calls[0][0]).toBe('eng');
  });

  it('clears the team when the owner picks Private on a shared room', () => {
    render(<RoomSharingDialog room={room({ team_id: 'team-eng' })} onClose={() => {}} />);

    const select = screen.getByLabelText('Shared with') as HTMLSelectElement;
    expect(select.value).toBe('eng');

    fireEvent.change(select, { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: /Save sharing/ }));

    expect(mocks.mutate).toHaveBeenCalledTimes(1);
    expect(mocks.mutate.mock.calls[0][0]).toBe('');
  });

  it('shows a viewer the reason and no control, even on a room they can read', () => {
    render(<RoomSharingDialog room={room({ team_id: 'team-eng', role: 'viewer' })} onClose={() => {}} />);

    expect(screen.queryByLabelText('Shared with')).toBeNull();
    expect(screen.queryByRole('button', { name: /Save sharing/ })).toBeNull();
    expect(screen.getByText(/Only the room's owner can change its sharing/)).toBeTruthy();
    expect(screen.getByText(/Engineering/)).toBeTruthy();
  });

  it('reports a refusal in the server words and keeps the dialog open', () => {
    mocks.isError = true;
    mocks.error = new Error('room "dev" not found');
    const onClose = vi.fn();
    render(<RoomSharingDialog room={room({ team_id: 'team-eng' })} onClose={onClose} />);

    expect(screen.getByText('room "dev" not found')).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
    // The owner can still choose something else rather than being stuck.
    expect(screen.getByRole('button', { name: /Save sharing/ })).toBeTruthy();
  });
});
