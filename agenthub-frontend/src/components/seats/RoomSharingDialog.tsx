/**
 * @fileoverview Room sharing - the one control that sets which team may read a room, and the reason a
 * non-owner sees no control at all.
 *
 * THE GATE IS THE WIRE'S OWN ANSWER, NOT A GUESS. `PUT /rooms/{room}/team` is owner-only: the handler
 * resolves the room through `GetRoomBySlug(userID, slug)`, which returns the caller's OWN room only,
 * and a team slug outside the caller's memberships is refused too - both a 404 in the server's words
 * (`seat_admin_mount.go:545-546`, `:710-760`). `GET /rooms` returns the caller's own rooms AND the
 * rooms shared with their teams, so the caller cannot tell the two apart without being told: the room
 * body carries `role` (`seatAdminRoomRole`, `seat_admin_mount.go:1687-1692`) for exactly this, and
 * this panel reads it. A viewer is therefore shown the read-only state and its reason up front,
 * never a control the server would refuse.
 *
 * The team list is the caller's own memberships (`GET /teams`), which is also the only set of slugs
 * the route accepts, so every option in the picker is settable.
 *
 * The dialog is mounted only while it is open (the page renders it under a flag), so each opening
 * starts from the room's current state and no stale error or stale selection can survive it.
 */

import React, { useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import Select from '../ui/select-simple';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { useSetRoomTeam, useTeams } from '../../hooks/useSeats';
import type { Room } from '../../types/seatTypes';

/** The empty team is how the route makes a room private again; it is a value, not an absence. */
const PRIVATE = '';

export interface RoomSharingDialogProps {
  room: Room;
  onClose: () => void;
}

export const RoomSharingDialog: React.FC<RoomSharingDialogProps> = ({ room, onClose }) => {
  const { teams, isLoading: teamsLoading } = useTeams();
  const setRoomTeam = useSetRoomTeam(room.slug);
  const [chosen, setChosen] = useState<string | null>(null);

  // The room body reports the sharing as a TEAM ID; the picker's options are SLUGS, so the current
  // value is the membership whose team is that id. An empty id means private; an id with no matching
  // membership means the room is still shared with a team this caller has since left.
  const sharedWith = teams.find((membership) => membership.team.id === room.team_id);
  const current = sharedWith?.team.slug ?? PRIVATE;
  const value = chosen ?? current;
  const isOwner = room.role === 'owner';

  const handleSave = () => {
    // The callback, not the hook, closes the dialog: a refusal keeps it open with the server's own
    // sentence where the button was (the same contract the delete-room dialog holds).
    setRoomTeam.mutate(value, { onSuccess: () => onClose() });
  };

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Sharing: {room.name}</DialogTitle>
          <DialogDescription>
            {isOwner
              ? 'Sharing lets a team read this room and its seats. Only you can change it, because you own the room.'
              : 'This room belongs to another user and is shared with a team you belong to.'}
          </DialogDescription>
        </DialogHeader>

        {!isOwner && (
          <p className="text-sm text-muted-foreground">
            Only the room's owner can change its sharing, so there is nothing to set here.
            {sharedWith && (
              <>
                {' '}
                You are reading it as a member of <span className="font-medium">{sharedWith.team.name}</span> (
                {sharedWith.team.slug}).
              </>
            )}
          </p>
        )}

        {isOwner && (
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="room-sharing-team">
              Shared with
            </label>
            <Select
              id="room-sharing-team"
              value={value}
              onChange={(event) => setChosen(event.target.value)}
              disabled={teamsLoading}
            >
              <option value={PRIVATE}>Private - only you</option>
              {teams.map((membership) => (
                <option key={membership.team.id} value={membership.team.slug}>
                  {membership.team.name} ({membership.team.slug})
                </option>
              ))}
            </Select>
            <p className="text-xs text-muted-foreground">
              Choosing Private clears the team, so the room is yours alone again.
            </p>
            {room.team_id !== '' && !sharedWith && (
              <p className="text-xs text-muted-foreground">
                This room is still shared with a team you are no longer a member of. Choosing a team below replaces
                it; Private clears it.
              </p>
            )}
          </div>
        )}

        {setRoomTeam.isError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{setRoomTeam.error.message}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {isOwner ? 'Cancel' : 'Close'}
          </Button>
          {isOwner && (
            <Button onClick={handleSave} disabled={setRoomTeam.isPending || value === current}>
              {setRoomTeam.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save sharing
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default RoomSharingDialog;
