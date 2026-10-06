/**
 * MachinesPanel - Live bridge status: one card per machine with its seats and herdr agents.
 *
 * @module components/seats/MachinesPanel
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AlertCircle, Loader2, Monitor } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { useMachines } from '../../hooks/useSeats';
import { driftedSeatCount } from '../../lib/machineSeats';
import type { MachineSeatStatus, MachineStatus, SeatRunState, SeatSync } from '../../types/seatTypes';

const STATE_CLASSES: Record<SeatRunState, string> = {
  running: 'bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-100',
  idle: 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  blocked: 'bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-100',
  stopped: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-100',
  unknown: 'bg-transparent text-gray-500 dark:text-gray-400',
};

export const SeatStateBadge: React.FC<{ state: SeatRunState }> = ({ state }) => (
  <Badge variant="outline" className={STATE_CLASSES[state] ?? STATE_CLASSES.unknown}>
    {state}
  </Badge>
);

const SYNC_CLASSES: Record<SeatSync, string> = {
  in_sync: 'bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-100',
  drift: 'bg-amber-50 text-amber-800 dark:bg-amber-900 dark:text-amber-100',
  unknown: 'bg-transparent text-gray-500 dark:text-gray-400',
};

const shortHash = (hash: string) => hash.slice(0, 8);

export const SeatSyncBadge: React.FC<{ seat: Pick<MachineSeatStatus, 'sync' | 'hash' | 'expected_hash'> }> = ({
  seat,
}) => {
  const className = SYNC_CLASSES[seat.sync] ?? SYNC_CLASSES.unknown;
  if (seat.sync === 'drift') {
    return (
      <Badge variant="outline" className={className}>
        drift · running {shortHash(seat.hash)} · expected {shortHash(seat.expected_hash)}
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className={className}>
      {seat.sync === 'in_sync' ? 'in sync' : 'sync unknown'}
    </Badge>
  );
};

/**
 * A seat a machine reports as live whose cloud record has no resolved snapshot. "sync unknown" alone
 * does not say this: it covers a missing running hash too, and the empty snapshot is the state worth
 * naming, because a seat that cannot resolve looks exactly like one nothing has resolved yet.
 */
export const SeatUnresolvedBadge: React.FC = () => (
  <Badge
    variant="destructive"
    title="A machine reports this seat as live, but the cloud has no resolved snapshot for it: nothing has resolved it."
  >
    no resolved snapshot
  </Badge>
);

const MachineCard: React.FC<{ machine: MachineStatus }> = ({ machine }) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-lg flex items-center justify-between">
        <span>{machine.machine_id}</span>
        <Badge variant={machine.online ? 'default' : 'destructive'}>
          {machine.online ? 'online' : 'offline'}
        </Badge>
      </CardTitle>
      <p className="text-xs text-muted-foreground">
        last seen {formatDistanceToNow(new Date(machine.last_seen), { addSuffix: true })}
      </p>
    </CardHeader>
    <CardContent className="space-y-3">
      {machine.seats.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="font-medium">Seat</th>
              <th className="font-medium">State</th>
              <th className="font-medium">Runtime</th>
              <th className="font-medium">Hash</th>
              <th className="font-medium">Sync</th>
              <th className="font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {machine.seats.map(seat => (
              <tr key={`${seat.room}/${seat.seat}`}>
                <td>
                  {seat.room}/{seat.seat}
                </td>
                <td>
                  <SeatStateBadge state={seat.state} />
                </td>
                <td>{seat.runtime}</td>
                <td className="font-mono">{shortHash(seat.hash)}</td>
                <td>
                  <SeatSyncBadge seat={seat} />
                </td>
                <td>
                  {seat.detail}
                  {seat.redacted && (
                    <Badge variant="secondary" className="ml-2">
                      redacted
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {machine.agents.length > 0 && (
        <ul className="flex flex-wrap gap-2 text-xs">
          {machine.agents.map(agent => (
            <li key={agent.pane_id}>
              <Badge variant="outline">
                {agent.agent} · {agent.status} · {agent.pane_id}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </CardContent>
  </Card>
);

export const MachinesPanel: React.FC = () => {
  const { machines, isLoading, error, refetch } = useMachines();
  const drifted = driftedSeatCount(machines);

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <Monitor className="h-5 w-5 text-primary" /> Bridge machines
        {drifted > 0 && (
          <Badge variant="outline" className={SYNC_CLASSES.drift}>
            {drifted} drifted
          </Badge>
        )}
      </h2>
      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading machines...
        </div>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error.message}
            <button className="ml-3 underline" onClick={() => refetch()}>
              Retry
            </button>
          </AlertDescription>
        </Alert>
      )}
      {!isLoading && !error && machines.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No bridge connected. Run scripts/openrig_bridge.py on your PC.
          </CardContent>
        </Card>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {machines.map(machine => (
          <MachineCard key={machine.machine_id} machine={machine} />
        ))}
      </div>
    </section>
  );
};
