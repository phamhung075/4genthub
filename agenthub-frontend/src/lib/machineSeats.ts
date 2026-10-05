import type { MachineSeatStatus, MachineStatus } from '../types/seatTypes';

/** Seats whose running hash differs from the latest resolved snapshot, across all machines. */
export function driftedSeatCount(machines: MachineStatus[]): number {
  return machines.reduce(
    (total, machine) => total + machine.seats.filter(seat => seat.sync === 'drift').length,
    0
  );
}

/** The most recently reported status of a room/seat across all machines, if any machine reports it. */
export function latestSeatStatus(
  machines: MachineStatus[],
  room: string,
  seat: string
): MachineSeatStatus | undefined {
  let latest: MachineSeatStatus | undefined;
  for (const machine of machines) {
    for (const reported of machine.seats) {
      if (
        reported.room === room &&
        reported.seat === seat &&
        (!latest || Date.parse(reported.reported_at) > Date.parse(latest.reported_at))
      ) {
        latest = reported;
      }
    }
  }
  return latest;
}
