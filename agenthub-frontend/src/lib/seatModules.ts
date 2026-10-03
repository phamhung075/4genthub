/**
 * Seat module resolution - mirror of the backend resolver for display.
 *
 * The backend is the source of truth; these helpers only show the user how the
 * seat type's module refs change once company, room and seat overlays apply.
 *
 * @module lib/seatModules
 * @version 1.0.0
 */

import type {
  EffectiveSeatModule,
  SeatOverlayScope,
  SeatOverlays,
  SeatTypeModuleRef,
} from '../types/seatTypes';

const SCOPE_ORDER: SeatOverlayScope[] = ['company', 'room', 'seat'];

export function computeEffectiveModules(
  refs: SeatTypeModuleRef[],
  overlays: SeatOverlays
): EffectiveSeatModule[] {
  const state = new Map<string, EffectiveSeatModule>();

  const ensure = (slug: string): EffectiveSeatModule => {
    const existing = state.get(slug);
    if (existing) {
      return existing;
    }
    const created: EffectiveSeatModule = {
      slug,
      version: 'latest',
      overridden: false,
      removed: false,
      changes: [],
    };
    state.set(slug, created);
    return created;
  };

  refs.forEach(ref => {
    ensure(ref.slug).version = ref.version || 'latest';
  });

  SCOPE_ORDER.forEach(scope => {
    const overlay = overlays[scope];
    if (!overlay) {
      return;
    }
    overlay.ops.forEach(op => {
      const module = ensure(op.slug);
      module.changes.push({ scope, kind: op.kind });
      switch (op.kind) {
        case 'add':
          module.version = op.version || 'latest';
          module.removed = false;
          break;
        case 'remove':
          module.removed = true;
          break;
        case 'override':
          module.overridden = true;
          module.contentOverride = op.content;
          break;
        case 'pin':
          module.version = op.version || module.version;
          break;
      }
    });
  });

  return Array.from(state.values());
}
