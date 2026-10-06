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

/**
 * A seat a machine reports as running, idle or blocked whose cloud record carries no resolved
 * snapshot: something launched it, yet nothing has resolved it. An unresolvable seat lands here,
 * because a refused resolve stores no snapshot, and so does a seat whose snapshot has simply not been
 * stored yet - the list can tell them apart from neither, so it names the fact it has. `expected_hash`
 * is the hash of the seat's newest stored snapshot, empty when none exists; stopped and unknown are
 * excluded, since nothing is expected to resolve a seat that is not running.
 */
export function isUnresolvedLiveSeat(seat: MachineSeatStatus): boolean {
  return seat.expected_hash === '' && seat.state !== 'stopped' && seat.state !== 'unknown';
}
