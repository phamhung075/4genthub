/**
 * Block composition - the frontend mirror of the resolver's overlay fold.
 *
 * The backend is the source of truth (`seat_management/domain/resolver/resolver.go`):
 * one state map starts from the seat type's module refs and is folded through the
 * company, room and seat overlays in that order. The fold is strict, so this module
 * models the two refusals the UI must never hide behind a silent no-op:
 *   - `add` of a block already in effect fails ("module already present");
 *   - `remove` of a block not in effect fails ("module not present").
 *
 * `origin` is the source label: the scope that first put the block into effect
 * (OpenRig's "every assembled piece names its source", profile-composer.ts).
 *
 * @module lib/blockComposition
 * @version 1.0.0
 */

import type {
  SeatOverlayOp,
  SeatOverlayScope,
  SeatOverlays,
  SeatTypeModuleRef,
} from '../types/seatTypes';

/** The fold order the resolver uses; company is the base layer, seat the most specific. */
export const BLOCK_SCOPE_ORDER: SeatOverlayScope[] = ['company', 'room', 'seat'];

/** Where a block came from: the seat type's published refs, or an overlay scope. */
export type BlockOrigin = 'seat-type' | SeatOverlayScope;

export interface ComposedBlock {
  slug: string;
  /** The version in effect after the fold. */
  version: string;
  /** The scope that first put this block into effect. */
  origin: BlockOrigin;
  /** The scope whose `pin` set the version, if any. */
  pinnedAt: BlockOrigin | null;
  /** True once an `override` replaced the module content. */
  overridden: boolean;
}

export interface ScopeComposition {
  scope: SeatOverlayScope;
  /** Blocks in effect after folding company..this scope. */
  present: ComposedBlock[];
  /** Slugs this scope's own ops removed. */
  removedHere: string[];
}

export interface BlockComposition {
  scopes: ScopeComposition[];
  /** Blocks in effect after the whole fold. */
  final: ComposedBlock[];
  /** Every slug the seat type or any op names, sorted. */
  known: string[];
}

/** One known block seen from one scope. */
export interface BlockAtScope {
  slug: string;
  /** In effect after folding company..this scope. */
  present: boolean;
  block: ComposedBlock | null;
  /** This scope carries a `remove` op for the slug. */
  removedHere: boolean;
}

export interface ActionOutcome {
  allowed: boolean;
  /** Why the resolver would refuse, when !allowed. */
  reason?: string;
  /** What an allowed action does, in the resolver's terms. */
  label?: string;
}

export function originLabel(origin: BlockOrigin): string {
  return origin === 'seat-type' ? 'the seat type' : origin;
}

/** Fold the seat type's refs through the three overlays, exactly as the resolver does. */
export function composeBlocks(
  refs: SeatTypeModuleRef[],
  overlays: SeatOverlays
): BlockComposition {
  const state: Record<string, ComposedBlock> = {};
  const known = new Set<string>();

  for (const ref of refs) {
    state[ref.slug] = {
      slug: ref.slug,
      version: ref.version,
      origin: 'seat-type',
      pinnedAt: null,
      overridden: false,
    };
    known.add(ref.slug);
  }

  const scopes: ScopeComposition[] = [];
  for (const scope of BLOCK_SCOPE_ORDER) {
    const ops = overlays[scope]?.ops ?? [];
    const removedHere: string[] = [];
    for (const op of ops) {
      known.add(op.slug);
      const existing = state[op.slug];
      switch (op.kind) {
        case 'add':
          // Re-adding a block a higher scope removed makes this scope its origin.
          state[op.slug] = {
            slug: op.slug,
            version: op.version,
            origin: scope,
            pinnedAt: null,
            overridden: false,
          };
          break;
        case 'remove':
          if (existing) {
            delete state[op.slug];
            removedHere.push(op.slug);
          }
          break;
        case 'override':
          if (existing) existing.overridden = true;
          break;
        case 'pin':
          if (existing) {
            existing.version = op.version;
            existing.pinnedAt = scope;
          }
          break;
      }
    }
    scopes.push({ scope, present: Object.values(state).map((block) => ({ ...block })), removedHere });
  }

  return {
    scopes,
    final: Object.values(state).map((block) => ({ ...block })),
    known: [...known].sort(),
  };
}

/** Every known block seen from one scope, so absent blocks can explain themselves rather than vanish. */
export function blocksAtScope(
  composition: BlockComposition,
  scope: SeatOverlayScope
): BlockAtScope[] {
  const entry = composition.scopes.find((step) => step.scope === scope);
  const present = new Set(entry?.present.map((block) => block.slug) ?? []);
  const removed = new Set(entry?.removedHere ?? []);
  return composition.known.map((slug) => ({
    slug,
    present: present.has(slug),
    block: entry?.present.find((block) => block.slug === slug) ?? null,
    removedHere: removed.has(slug),
  }));
}

/**
 * What removing the block at `scope` does. A removal that cannot apply is refused
 * with the resolver's reason, never offered as a no-op.
 */
export function removalOutcome(entry: BlockAtScope, scope: SeatOverlayScope): ActionOutcome {
  if (!entry.present) {
    return {
      allowed: false,
      reason: entry.removedHere
        ? `already removed at ${scope}: the resolver refuses a second remove`
        : `not in effect at ${scope}: there is nothing to remove here`,
    };
  }
  const origin = entry.block?.origin ?? 'seat-type';
  if (origin === scope) {
    return { allowed: true, label: `removed at ${scope}; this level is the only definition` };
  }
  return { allowed: true, label: `removed at ${scope} · still defined at ${originLabel(origin)}` };
}

/** What adding the block at `scope` does; refused when it is already in effect there. */
export function additionOutcome(entry: BlockAtScope, scope: SeatOverlayScope): ActionOutcome {
  if (entry.present) {
    return {
      allowed: false,
      reason: `already in effect at ${scope}: the resolver refuses a second add`,
    };
  }
  return { allowed: true, label: `added at ${scope}` };
}

/** The scope's ops with one add appended (read-modify-write of the whole overlay). */
export function withAddedBlock(ops: SeatOverlayOp[], slug: string, version: string): SeatOverlayOp[] {
  return [...ops, { kind: 'add', slug, version, content: '' }];
}

/**
 * The scope's ops after removing one block: an `add` this scope made is undone by
 * dropping that op; anything inherited above gets a `remove` op appended.
 */
export function withRemovedBlock(ops: SeatOverlayOp[], slug: string): SeatOverlayOp[] {
  const addedHere = ops.some((op) => op.kind === 'add' && op.slug === slug);
  if (addedHere) {
    return ops.filter((op) => !(op.kind === 'add' && op.slug === slug));
  }
  return [...ops, { kind: 'remove', slug, version: '', content: '' }];
}

/** Undo this scope's `remove` for a slug, restoring what is inherited from above. */
export function withRestoredBlock(ops: SeatOverlayOp[], slug: string): SeatOverlayOp[] {
  return ops.filter((op) => !(op.kind === 'remove' && op.slug === slug));
}
