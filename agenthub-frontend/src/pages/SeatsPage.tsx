/**
 * Seats Page - Rooms and the fixed seats inside them.
 *
 * Seats are stable role slots; the occupant is a replaceable brain and modules
 * are lego blocks. This page manages rooms, seats and the company pin policy.
 *
 * @module pages/SeatsPage
 * @version 1.0.0
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, DoorOpen, Loader2, Plus, Trash2, Users } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select-simple';
import { MachinesPanel, SeatStateBadge, SeatSyncBadge } from '../components/seats/MachinesPanel';
import { latestSeatStatus } from '../lib/machineSeats';
import { isValidSeatName, SEAT_NAME_MESSAGE } from '../lib/seatNames';
import {
  useCreateRoom,
  useCreateSeat,
  useMachines,
  useRemoveSeat,
  useRooms,
  useSeatSettings,
  useSeatTypes,
  useSeats,
  useUpdateSeatSettings,
} from '../hooks/useSeats';
import { SEAT_RUNTIMES } from '../types/seatTypes';
import type { Seat, SeatPinChoice, SeatRuntime } from '../types/seatTypes';

const pinLabel = (seat: Seat) =>
  seat.pinned_version ? `Pinned ${seat.pinned_version}` : 'Follows latest';


export const SeatsPage: React.FC = () => {
  const navigate = useNavigate();
  const { rooms, isLoading: roomsLoading, error: roomsError, refetch: refetchRooms } = useRooms();
  const { seatTypes, isLoading: seatTypesLoading } = useSeatTypes();
  const { settings, isLoading: settingsLoading, error: settingsError, refetch: refetchSettings } =
    useSeatSettings();
  const updateSettings = useUpdateSeatSettings();
  const createRoom = useCreateRoom();
  const { machines } = useMachines();

  const [selectedRoom, setSelectedRoom] = useState('');
  const { seats, isLoading: seatsLoading, error: seatsError, refetch: refetchSeats } = useSeats(selectedRoom);
  const createSeat = useCreateSeat(selectedRoom);
  const removeSeat = useRemoveSeat(selectedRoom);

  const [roomSlug, setRoomSlug] = useState('');
  const [roomName, setRoomName] = useState('');

  const [addSeatOpen, setAddSeatOpen] = useState(false);
  const [seatForm, setSeatForm] = useState({
    seat_key: '',
    seat_type: '',
    runtime: 'claude-code' as SeatRuntime,
    model: '',
    pin: 'company-default' as SeatPinChoice,
  });

  const [seatToRemove, setSeatToRemove] = useState<Seat | null>(null);

  const roomSlugValid = isValidSeatName(roomSlug);
  const roomSlugInvalid = roomSlug !== '' && !roomSlugValid;
  const seatKeyValid = isValidSeatName(seatForm.seat_key);
  const seatKeyInvalid = seatForm.seat_key !== '' && !seatKeyValid;

  const handleCreateRoom = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!roomSlugValid || !roomName.trim()) {
      return;
    }
    const response = await createRoom.mutateAsync({ slug: roomSlug.trim(), name: roomName.trim() });
    setRoomSlug('');
    setRoomName('');
    setSelectedRoom(response.room.slug);
  };

  const handleAddSeat = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!seatKeyValid || !seatForm.seat_type || !seatForm.model.trim()) {
      return;
    }
    const body = {
      seat_key: seatForm.seat_key.trim(),
      seat_type: seatForm.seat_type,
      runtime: seatForm.runtime,
      model: seatForm.model.trim(),
    } as { seat_key: string; seat_type: string; runtime: SeatRuntime; model: string; follow_latest?: boolean };

    if (seatForm.pin === 'pin-latest') {
      body.follow_latest = false;
    } else if (seatForm.pin === 'follow-latest') {
      body.follow_latest = true;
    }

    await createSeat.mutateAsync(body);
    setAddSeatOpen(false);
    setSeatForm({ seat_key: '', seat_type: '', runtime: 'claude-code', model: '', pin: 'company-default' });
  };

  const handleRemoveSeat = async () => {
    if (!seatToRemove) {
      return;
    }
    await removeSeat.mutateAsync(seatToRemove.seat_key);
    setSeatToRemove(null);
  };

  const seatTypeOptions = seatTypes.map(type => (
    <option key={type.slug} value={type.slug}>
      {type.name} ({type.slug})
    </option>
  ));

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Seats</h1>
          <p className="text-muted-foreground mt-2">
            Rooms hold fixed role slots. Each seat's occupant and modules are replaceable.
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate('/seats/authoring')}>
          Author modules and seat types
        </Button>
      </div>

      {/* Company pin policy */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Company version policy</CardTitle>
          <CardDescription>
            Pinning is the default: a new seat pins the seat type's latest version and only changes when a
            new version is published. Turn this on to let new seats follow the latest version instead.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {settingsLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading settings...
            </div>
          )}
          {settingsError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {settingsError.message}
                <Button variant="outline" size="sm" className="ml-3" onClick={() => refetchSettings()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!settingsLoading && !settingsError && settings && (
            <label className="flex items-center gap-3 cursor-pointer w-fit">
              <Checkbox
                aria-label="Follow latest by default"
                checked={settings.follow_latest}
                disabled={updateSettings.isPending}
                onCheckedChange={checked => updateSettings.mutate(checked)}
              />
              <span className="text-sm font-medium">
                Follow latest seat type versions by default
              </span>
            </label>
          )}
          {updateSettings.isError && (
            <Alert variant="destructive" className="mt-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{updateSettings.error.message}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Create room */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Create a room</CardTitle>
          <CardDescription>A room groups seats, like a team or pod.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleCreateRoom}>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="room-slug">
                Room slug
              </label>
              <Input
                id="room-slug"
                aria-label="Room slug"
                aria-invalid={roomSlugInvalid}
                aria-describedby={roomSlugInvalid ? 'room-slug-error' : undefined}
                value={roomSlug}
                onChange={e => setRoomSlug(e.target.value)}
                placeholder="engineering"
              />
              {roomSlugInvalid && (
                <p id="room-slug-error" className="text-xs text-destructive">
                  {SEAT_NAME_MESSAGE}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="room-name">
                Room name
              </label>
              <Input
                id="room-name"
                aria-label="Room name"
                value={roomName}
                onChange={e => setRoomName(e.target.value)}
                placeholder="Engineering"
              />
            </div>
            <Button type="submit" disabled={createRoom.isPending || !roomSlugValid || !roomName.trim()}>
              {createRoom.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Create room
            </Button>
          </form>
          {createRoom.isError && (
            <Alert variant="destructive" className="mt-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{createRoom.error.message}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Rooms */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <DoorOpen className="h-5 w-5 text-primary" /> Rooms
        </h2>
        <p className="text-xs text-muted-foreground">A room is an OpenRig pod.</p>
        {roomsLoading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading rooms...
          </div>
        )}
        {roomsError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {roomsError.message}
              <Button variant="outline" size="sm" className="ml-3" onClick={() => refetchRooms()}>
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}
        {!roomsLoading && !roomsError && rooms.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No rooms yet. Create one above to start adding seats.
            </CardContent>
          </Card>
        )}
        <div className="flex flex-wrap gap-2">
          {rooms.map(room => (
            <Button
              key={room.id}
              variant={selectedRoom === room.slug ? 'default' : 'outline'}
              onClick={() => setSelectedRoom(room.slug)}
            >
              {room.name}
              <span className="ml-2 text-xs opacity-70">{room.slug}</span>
            </Button>
          ))}
        </div>
      </section>

      {/* Seats in the selected room */}
      {selectedRoom && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" /> Seats in {selectedRoom}
            </h2>
            <Button onClick={() => setAddSeatOpen(true)} disabled={seatTypesLoading}>
              <Plus className="h-4 w-4" /> Add seat
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            A seat is an OpenRig member (a fixed role slot).
          </p>

          {seatsLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading seats...
            </div>
          )}
          {seatsError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {seatsError.message}
                <Button variant="outline" size="sm" className="ml-3" onClick={() => refetchSeats()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!seatsLoading && !seatsError && seats.length === 0 && (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                This room has no seats yet.
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {seats.map(seat => {
              const live = latestSeatStatus(machines, selectedRoom, seat.seat_key);
              return (
              <Card key={seat.id}>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>{seat.seat_key}</span>
                    <span className="flex items-center gap-2">
                      {live && <SeatStateBadge state={live.state} />}
                      {live && <SeatSyncBadge seat={live} />}
                      <Badge variant="outline">{seat.status}</Badge>
                    </span>
                  </CardTitle>
                  <CardDescription>{seat.seat_type}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Type</span>
                      <p className="font-medium">{seat.seat_type}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Runtime</span>
                      <p className="font-medium">{seat.runtime}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Model</span>
                      <p className="font-medium">{seat.model || '—'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Version</span>
                      <p className="font-medium">{pinLabel(seat)}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        navigate(
                          `/seats/${encodeURIComponent(selectedRoom)}/${encodeURIComponent(seat.seat_key)}`
                        )
                      }
                    >
                      Details <ArrowRight className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      aria-label={`Remove seat ${seat.seat_key}`}
                      onClick={() => setSeatToRemove(seat)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
              );
            })}
          </div>
        </section>
      )}

      <MachinesPanel />

      {/* Add seat dialog */}
      <Dialog open={addSeatOpen} onOpenChange={setAddSeatOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Add a seat</DialogTitle>
            <DialogDescription>
              A seat keeps its key forever; the seat type defines its base modules and the occupant is
              replaceable.
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleAddSeat}>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="seat-key">
                Seat key
              </label>
              <Input
                id="seat-key"
                aria-label="Seat key"
                aria-invalid={seatKeyInvalid}
                aria-describedby={seatKeyInvalid ? 'seat-key-error' : undefined}
                value={seatForm.seat_key}
                onChange={e => setSeatForm(prev => ({ ...prev, seat_key: e.target.value }))}
                placeholder="alice"
                required
              />
              {seatKeyInvalid && (
                <p id="seat-key-error" className="text-xs text-destructive">
                  {SEAT_NAME_MESSAGE}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="seat-type">
                Seat type
              </label>
              <Select
                id="seat-type"
                aria-label="Seat type"
                value={seatForm.seat_type}
                onChange={e => setSeatForm(prev => ({ ...prev, seat_type: e.target.value }))}
                required
              >
                <option value="">Select a seat type</option>
                {seatTypeOptions}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="seat-runtime">
                  Runtime
                </label>
                <Select
                  id="seat-runtime"
                  aria-label="Runtime"
                  value={seatForm.runtime}
                  onChange={e => setSeatForm(prev => ({ ...prev, runtime: e.target.value as SeatRuntime }))}
                >
                  {SEAT_RUNTIMES.map(runtime => (
                    <option key={runtime} value={runtime}>
                      {runtime}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="seat-model">
                  Model
                </label>
                <Input
                  id="seat-model"
                  aria-label="Model"
                  value={seatForm.model}
                  onChange={e => setSeatForm(prev => ({ ...prev, model: e.target.value }))}
                  placeholder="sonnet"
                />
              </div>
            </div>

            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">Version policy</legend>
              {(
                [
                  ['pin-latest', 'Pin to latest'],
                  ['follow-latest', 'Follow latest'],
                  ['company-default', 'Use company default'],
                ] as [SeatPinChoice, string][]
              ).map(([value, label]) => (
                <label key={value} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    name="seat-pin"
                    value={value}
                    checked={seatForm.pin === value}
                    onChange={() => setSeatForm(prev => ({ ...prev, pin: value }))}
                  />
                  {label}
                </label>
              ))}
            </fieldset>

            {createSeat.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{createSeat.error.message}</AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddSeatOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  createSeat.isPending || !seatKeyValid || !seatForm.seat_type || !seatForm.model.trim()
                }
              >
                {createSeat.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Add seat
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Remove confirmation */}
      <Dialog open={!!seatToRemove} onOpenChange={open => !open && setSeatToRemove(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Remove seat?</DialogTitle>
            <DialogDescription>
              Seat "{seatToRemove?.seat_key}" will be marked removed. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSeatToRemove(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleRemoveSeat} disabled={removeSeat.isPending}>
              {removeSeat.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Remove seat
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
