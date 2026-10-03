/**
 * Seat names - OpenRig room slugs (pod ids) and seat keys (member ids).
 *
 * Both must start with a letter or digit and contain only letters, digits,
 * "_" or "-" (no dots or spaces).
 *
 * @module lib/seatNames
 * @version 1.0.0
 */

export const SEAT_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

export const SEAT_NAME_MESSAGE =
  'Use letters, digits, "_" or "-"; start with a letter or digit (no dots or spaces).';

export function isValidSeatName(value: string): boolean {
  return SEAT_NAME_PATTERN.test(value);
}

export const SEAT_MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;

export const SEAT_MODEL_MESSAGE =
  'Use letters, digits, ".", "_", ":", "/" or "-"; start with a letter or digit.';

/** An empty model is valid: the runtime default is used. */
export function isValidSeatModel(value: string): boolean {
  return value === '' || SEAT_MODEL_PATTERN.test(value);
}
