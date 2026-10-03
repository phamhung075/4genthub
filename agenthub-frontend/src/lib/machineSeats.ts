import type { MachineSeatStatus, MachineStatus } from '../types/seatTypes';

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
