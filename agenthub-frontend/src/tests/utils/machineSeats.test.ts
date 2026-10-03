/**
 * @fileoverview Test suite for machineSeats utility
 * Tests the drifted seat count across bridge machines.
 */

import { driftedSeatCount } from '../../lib/machineSeats';
import type { MachineSeatStatus, MachineStatus } from '../../types/seatTypes';

const machineSeat = (sync: MachineSeatStatus['sync']): MachineSeatStatus => ({
  room: 'dev',
  seat: 'alice',
  state: 'running',
  runtime: 'claude-code',
  hash: 'aaaaaaaa11111111',
  expected_hash: 'bbbbbbbb22222222',
  sync,
  detail: '',
  redacted: false,
  reported_at: '2025-01-01T00:00:00.000Z',
});

const machine = (machine_id: string, seats: MachineSeatStatus[]): MachineStatus => ({
  machine_id,
  last_seen: '2025-01-01T00:00:00.000Z',
  online: true,
  seats,
  agents: [],
});

describe('driftedSeatCount', () => {
  it('returns 0 for an empty machine list', () => {
    expect(driftedSeatCount([])).toBe(0);
  });

  it('returns 0 for machines that report no seats', () => {
    expect(driftedSeatCount([machine('pc-home', []), machine('pc-work', [])])).toBe(0);
  });

  it('counts only drift seats across mixed in_sync/drift/unknown reports', () => {
    const machines = [
      machine('pc-home', [machineSeat('drift'), machineSeat('in_sync'), machineSeat('unknown')]),
      machine('pc-work', [machineSeat('drift'), machineSeat('drift'), machineSeat('in_sync')]),
    ];

    expect(driftedSeatCount(machines)).toBe(3);
  });
});
