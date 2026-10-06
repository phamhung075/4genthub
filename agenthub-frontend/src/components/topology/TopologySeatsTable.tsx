/**
 * TopologySeatsTable - every seat in the workspace as one row, the tabular half
 * of F6 next to the graph.
 *
 * @module components/topology/TopologySeatsTable
 * @version 1.0.0
 */

import React from 'react';
import type { RoomTopology } from '../../hooks/useTopology';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';

const pinLabel = (pinned: string | null): string => (pinned ? pinned : 'follows latest');

export const TopologySeatsTable: React.FC<{ rooms: RoomTopology[] }> = ({ rooms }) => {
  const rows = rooms.flatMap((entry) =>
    entry.seats.map((seat) => ({ room: entry.room, seat }))
  );

  if (rows.length === 0) {
    return <p className="p-4 text-sm text-base-secondary">No seats in any room yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Room</TableHead>
          <TableHead>Seat</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Runtime</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Policy</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(({ room, seat }) => (
          <TableRow key={seat.id}>
            <TableCell>{room.name}</TableCell>
            <TableCell className="font-medium">{seat.seat_key}</TableCell>
            <TableCell>{seat.seat_type}</TableCell>
            <TableCell>{seat.runtime}</TableCell>
            {/* A runtime default applies when no model is set (measured); which one is unestablished, so the
                cell names only that. This service stores blank. */}
            <TableCell>{seat.model || 'runtime default'}</TableCell>
            <TableCell>{pinLabel(seat.pinned_version)}</TableCell>
            <TableCell>{seat.permission_policy}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
