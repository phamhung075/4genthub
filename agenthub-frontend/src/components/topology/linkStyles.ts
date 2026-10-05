/**
 * Link styling - one colour and dash per edge kind, labels shared with the seat
 * pages so a kind is named the same everywhere (`SEAT_LINK_KINDS`).
 *
 * @module components/topology/linkStyles
 * @version 1.0.0
 */

import type { SeatLinkKind } from '../../types/seatTypes';
import { SEAT_LINK_KINDS } from '../../types/seatTypes';

export interface LinkStyle {
  label: string;
  hint: string;
  color: string;
  /** SVG stroke-dasharray; undefined is a solid line. */
  dash: string | undefined;
}

const COLOR: Record<SeatLinkKind, string> = {
  delegates_to: '#2563eb',
  spawned_by: '#7c3aed',
  can_observe: '#64748b',
  collaborates_with: '#0891b2',
  escalates_to: '#dc2626',
};

const DASH: Record<SeatLinkKind, string | undefined> = {
  delegates_to: undefined,
  spawned_by: '6 4',
  can_observe: '2 4',
  collaborates_with: undefined,
  escalates_to: '1 4',
};

/** Keyed by kind; labels and hints come from the single source in seatTypes. */
export const LINK_STYLES = Object.fromEntries(
  SEAT_LINK_KINDS.map((option) => [
    option.kind,
    { label: option.label, hint: option.hint, color: COLOR[option.kind], dash: DASH[option.kind] },
  ])
) as Record<SeatLinkKind, LinkStyle>;
