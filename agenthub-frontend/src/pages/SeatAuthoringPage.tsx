/**
 * Seat Authoring Page - compose a seat from blocks, and author the blocks.
 *
 * The composition surface is the headline: pick a seat and a level (company, room
 * or seat) and add or remove one block at a time, seeing where each block is
 * inherited from and what a removal at that level does. Below it stay the two
 * authoring forms without which there would be nothing to compose: publishing a
 * module version and publishing a seat type version.
 *
 * @module pages/SeatAuthoringPage
 * @version 1.1.0
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select } from '../components/ui/select-simple';
import { ModulePublishForm } from '../components/seats/ModulePublishForm';
import { McpBlockForm } from '../components/seats/McpBlockForm';
import { SeatComposer } from '../components/seats/SeatComposer';
import { SeatTypeVersionForm } from '../components/seats/SeatTypeVersionForm';
import {
  useMcpServers,
  useModules,
  useRooms,
  useSeatOverlays,
  useSeatTypes,
  useSeats,
  useUpdateOverlay,
} from '../hooks/useSeats';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../hooks/useWebSocketV2';
import { useRealtimeSync } from '../hooks/useRealtimeSync';
import type { SeatOverlayOp, SeatOverlayScope } from '../types/seatTypes';

export const SeatAuthoringPage: React.FC = () => {
  const navigate = useNavigate();

  // Live seat sync: module, seat-type and overlay changes arrive over the same socket.
  const { user, tokens } = useAuth();
  const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
  useRealtimeSync(webSocketClient.client, true);

  const { seatTypes, isLoading, error, refetch } = useSeatTypes();
  const { modules, isLoading: modulesLoading, error: modulesError, refetch: refetchModules } = useModules();
  const mcpServers = useMcpServers(modules);
  const { rooms } = useRooms();

  const [room, setRoom] = useState('');
  const [seat, setSeat] = useState('');
  const roomSlug = rooms.some((entry) => entry.slug === room) ? room : rooms[0]?.slug ?? '';
  const { seats } = useSeats(roomSlug);
  const seatKey = seats.some((entry) => entry.seat_key === seat) ? seat : seats[0]?.seat_key ?? '';

  const {
    companyOverlay,
    roomOverlay,
    seatOverlay,
    error: overlaysError,
  } = useSeatOverlays(roomSlug, seatKey);
  const updateOverlay = useUpdateOverlay(roomSlug, seatKey);

  const selectedSeat = seats.find((entry) => entry.seat_key === seatKey);
  const selectedSeatType = seatTypes.find((type) => type.slug === selectedSeat?.seat_type);

  const handleApply = (scope: SeatOverlayScope, ops: SeatOverlayOp[]) => {
    updateOverlay.mutate({ scope, ops });
  };

  const composerError = updateOverlay.isError
    ? updateOverlay.error.message
    : overlaysError
      ? overlaysError.message
      : null;

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Seat authoring</h1>
          <p className="text-muted-foreground mt-2">
            Compose a seat from blocks one at a time, then author the modules and seat types those blocks come from.
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate('/seats')}>
          Back to seats
        </Button>
      </div>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-56">
            <label className="text-sm font-medium" htmlFor="compose-room">
              Room
            </label>
            <Select
              id="compose-room"
              aria-label="Compose room"
              value={roomSlug}
              onChange={(event) => setRoom(event.target.value)}
            >
              {rooms.map((entry) => (
                <option key={entry.id} value={entry.slug}>
                  {entry.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="w-56">
            <label className="text-sm font-medium" htmlFor="compose-seat">
              Seat
            </label>
            <Select
              id="compose-seat"
              aria-label="Compose seat"
              value={seatKey}
              onChange={(event) => setSeat(event.target.value)}
            >
              {seats.map((entry) => (
                <option key={entry.id} value={entry.seat_key}>
                  {entry.seat_key}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {rooms.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No rooms yet. Create a room and a seat before composing a seat.
          </p>
        ) : seats.length === 0 ? (
          <p className="text-sm text-muted-foreground">This room has no seats yet.</p>
        ) : (
          <SeatComposer
            room={roomSlug}
            seat={seatKey}
            seatType={selectedSeatType}
            modules={modules}
            mcpServers={mcpServers}
            overlays={{ company: companyOverlay, room: roomOverlay, seat: seatOverlay }}
            isSaving={updateOverlay.isPending}
            saveError={composerError}
            onApply={handleApply}
          />
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Modules</CardTitle>
          <CardDescription>The latest published version of each module.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {modulesLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading modules...
            </div>
          )}
          {modulesError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {modulesError.message}
                <Button variant="outline" size="sm" className="ml-3" onClick={() => refetchModules()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!modulesLoading && !modulesError && modules.length === 0 && (
            <p className="text-sm text-muted-foreground">No modules yet.</p>
          )}
          {modules.map(module => (
            <div key={module.slug} className="flex flex-wrap items-center gap-2 rounded-md border p-3">
              <span className="font-mono font-medium">{module.slug}</span>
              <Badge variant="secondary">{module.kind}</Badge>
              <Badge variant="outline">{module.version}</Badge>
              {/* A producer can OMIT sha256 - the type only claims it is present - and an optional
                  chain plus a named fallback is this codebase's house form for that absence
                  (types/websocket-protocol.ts:473). Without it the missing key threw during render
                  and unmounted the whole page instead of degrading this one cell. */}
              <code className="text-xs text-muted-foreground">{module.sha256?.substring(0, 8) || 'unknown'}</code>
            </div>
          ))}
        </CardContent>
      </Card>

      <ModulePublishForm />

      <McpBlockForm />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Seat types</CardTitle>
          <CardDescription>Each seat type, its default runtime and its latest version's modules.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading seat types...
            </div>
          )}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {error.message}
                <Button variant="outline" size="sm" className="ml-3" onClick={() => refetch()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!isLoading && !error && seatTypes.length === 0 && (
            <p className="text-sm text-muted-foreground">No seat types yet.</p>
          )}
          {seatTypes.map(type => (
            <div key={type.slug} className="rounded-md border p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{type.name}</span>
                <code className="text-xs text-muted-foreground">{type.slug}</code>
                <Badge variant="secondary">{type.default_runtime ?? 'no runtime'}</Badge>
                <Badge variant="outline">{type.latest_version ?? 'no version'}</Badge>
              </div>
              {type.description && <p className="text-sm text-muted-foreground">{type.description}</p>}
              <div className="flex flex-wrap gap-1">
                {type.module_refs.map(ref => (
                  <Badge key={`${ref.slug}@${ref.version}`} variant="outline" className="font-mono">
                    {ref.slug}@{ref.version}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <SeatTypeVersionForm seatTypes={seatTypes} />
    </div>
  );
};
