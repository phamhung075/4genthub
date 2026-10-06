/**
 * TopologyGraph - rooms as groups, seats as nodes, seat links as edges drawn by
 * kind. Hand-rolled SVG: the app carries no graph layout dependency, and one
 * deterministic grid per room is enough for the workspace sizes this renders.
 *
 * @module components/topology/TopologyGraph
 * @version 1.0.0
 */

import React from 'react';
import type { RoomTopology } from '../../hooks/useTopology';
import type { Seat, SeatLink } from '../../types/seatTypes';
import { LINK_STYLES, type LinkStyle } from './linkStyles';

interface Point {
  x: number;
  y: number;
}

const BOX_W = 168;
const BOX_H = 72;
const GAP_X = 32;
const GAP_Y = 28;
const PAD = 8;
const MAX_COLS = 3;

/** Deterministic grid: never wider than MAX_COLS, columns grow with the seat count. */
function layout(seats: Seat[]): Record<string, Point> {
  const cols = Math.max(1, Math.min(MAX_COLS, Math.ceil(Math.sqrt(seats.length))));
  const positions: Record<string, Point> = {};
  seats.forEach((seat, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    positions[seat.id] = {
      x: PAD + col * (BOX_W + GAP_X) + BOX_W / 2,
      y: PAD + row * (BOX_H + GAP_Y) + BOX_H / 2,
    };
  });
  return positions;
}

function svgSize(seatCount: number): { width: number; height: number } {
  const cols = Math.max(1, Math.min(MAX_COLS, Math.ceil(Math.sqrt(seatCount))));
  const rows = Math.ceil(seatCount / cols) || 1;
  return {
    width: cols * BOX_W + (cols - 1) * GAP_X + PAD * 2,
    height: rows * BOX_H + (rows - 1) * GAP_Y + PAD * 2,
  };
}

function SeatNode({ seat, point }: { seat: Seat; point: Point }) {
  return (
    <g transform={`translate(${point.x - BOX_W / 2}, ${point.y - BOX_H / 2})`}>
      <rect
        width={BOX_W}
        height={BOX_H}
        rx={8}
        className="fill-background stroke-gray-300 dark:stroke-gray-600"
      />
      <text x={10} y={22} className="fill-current text-sm font-medium">
        {seat.seat_key}
      </text>
      <text x={10} y={40} className="fill-current text-xs opacity-70">
        {seat.seat_type} · {seat.runtime}
      </text>
      {/* The runtime substitutes a default when handed none (measured); WHICH default it picks is not
          established, so the label names only that a runtime default applies. This service stores blank. */}
      <text x={10} y={58} className="fill-current text-xs opacity-70">
        {seat.model || 'runtime default'}
      </text>
    </g>
  );
}

function Edge({
  from,
  to,
  link,
  style,
}: {
  from: Point;
  to: Point;
  link: SeatLink;
  style: LinkStyle;
}) {
  return (
    <line
      x1={from.x}
      y1={from.y}
      x2={to.x}
      y2={to.y}
      stroke={style.color}
      strokeWidth={2}
      strokeDasharray={link.allow ? style.dash : '1 3'}
      opacity={link.allow ? 0.9 : 0.5}
      markerEnd="url(#topology-arrow)"
      data-link-kind={link.kind}
      data-link-allow={link.allow}
    />
  );
}

function RoomGroup({ entry }: { entry: RoomTopology }) {
  const { room, seats, links } = entry;
  const positions = layout(seats);
  const { width, height } = svgSize(seats.length);

  return (
    <section className="rounded-lg border border-surface-border-hover p-4">
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="font-semibold text-base-primary">{room.name}</h3>
        <span className="text-xs text-base-secondary">
          {room.slug} · {seats.length} {seats.length === 1 ? 'seat' : 'seats'}
        </span>
      </header>

      {seats.length === 0 ? (
        <p className="py-6 text-center text-sm text-base-secondary">No seats in this room.</p>
      ) : (
        <svg
          role="img"
          aria-label={`${room.name} topology`}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          className="max-w-full"
        >
          <defs>
            <marker
              id="topology-arrow"
              viewBox="0 0 10 10"
              refX="10"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" className="text-gray-400" />
            </marker>
          </defs>

          {links.map((link) => {
            const from = positions[link.from_seat_id];
            const to = positions[link.to_seat_id];
            if (!from || !to) return null;
            return (
              <Edge
                key={link.id}
                from={from}
                to={to}
                link={link}
                style={LINK_STYLES[link.kind]}
              />
            );
          })}

          {seats.map((seat) => {
            const point = positions[seat.id];
            return point ? <SeatNode key={seat.id} seat={seat} point={point} /> : null;
          })}
        </svg>
      )}
    </section>
  );
}

/** Legend: one swatch per kind, so a colour on the graph is readable. */
export function TopologyLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-base-secondary" role="list">
      {Object.entries(LINK_STYLES).map(([kind, style]) => (
        <li key={kind} className="flex items-center gap-2">
          <svg width="28" height="8" aria-hidden="true">
            <line
              x1="0"
              y1="4"
              x2="28"
              y2="4"
              stroke={style.color}
              strokeWidth="2"
              strokeDasharray={style.dash}
            />
          </svg>
          <span>{style.label}</span>
        </li>
      ))}
      <li className="flex items-center gap-2">
        <svg width="28" height="8" aria-hidden="true">
          <line x1="0" y1="4" x2="28" y2="4" stroke="#94a3b8" strokeWidth="2" strokeDasharray="1 3" opacity="0.5" />
        </svg>
        <span>Denied</span>
      </li>
    </ul>
  );
}

export const TopologyGraph: React.FC<{ rooms: RoomTopology[] }> = ({ rooms }) => (
  <div className="grid gap-4 xl:grid-cols-2">
    {rooms.map((entry) => (
      <RoomGroup key={entry.room.id} entry={entry} />
    ))}
  </div>
);
