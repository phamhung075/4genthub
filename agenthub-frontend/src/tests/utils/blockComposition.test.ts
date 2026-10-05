/**
 * @fileoverview blockComposition folds the overlays exactly as the Go resolver
 * does and answers, per level, what a removal or an addition actually does.
 */

import {
  additionOutcome,
  blocksAtScope,
  composeBlocks,
  originLabel,
  removalOutcome,
  withAddedBlock,
  withRemovedBlock,
  withRestoredBlock,
} from '../../lib/blockComposition';
import type { SeatOverlays, SeatOverlayScope, SeatOverlayOp } from '../../types/seatTypes';

const emptyOverlays = (): SeatOverlays => ({
  company: { scope: 'company', ops: [] },
  room: { scope: 'room', ops: [] },
  seat: { scope: 'seat', ops: [] },
});

const withOps = (scope: SeatOverlayScope, ops: SeatOverlayOp[]): SeatOverlays => ({
  ...emptyOverlays(),
  [scope]: { scope, ops },
});

const entry = (overlays: SeatOverlays, scope: SeatOverlayScope, slug: string) => {
  const row = blocksAtScope(composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays), scope).find(
    (candidate) => candidate.slug === slug
  );
  if (!row) throw new Error(`no block ${slug} at ${scope}`);
  return row;
};

describe('composeBlocks', () => {
  it('starts from the seat type refs and labels them as the seat type origin', () => {
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], emptyOverlays());

    expect(composition.known).toEqual(['rules']);
    expect(composition.final).toEqual([
      { slug: 'rules', version: '1.0.0', origin: 'seat-type', pinnedAt: null, overridden: false },
    ]);
  });

  it('keeps an added block inherited from the scope that added it', () => {
    const overlays = withOps('company', [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }]);
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    // Present from company on, and still present at the more specific scopes.
    expect(blocksAtScope(composition, 'company').find((b) => b.slug === 'style')?.block?.origin).toBe('company');
    expect(blocksAtScope(composition, 'seat').find((b) => b.slug === 'style')?.block?.origin).toBe('company');
  });

  it('removes at a scope and records it there', () => {
    const overlays = withOps('seat', [{ kind: 'remove', slug: 'rules', version: '', content: '' }]);
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    expect(blocksAtScope(composition, 'room').find((b) => b.slug === 'rules')?.present).toBe(true);
    const atSeat = blocksAtScope(composition, 'seat').find((b) => b.slug === 'rules');
    expect(atSeat?.present).toBe(false);
    expect(atSeat?.removedHere).toBe(true);
    expect(composition.final).toEqual([]);
  });

  it('makes a re-added block owned by the scope that re-added it', () => {
    const overlays: SeatOverlays = {
      ...emptyOverlays(),
      company: { scope: 'company', ops: [{ kind: 'remove', slug: 'rules', version: '', content: '' }] },
      seat: { scope: 'seat', ops: [{ kind: 'add', slug: 'rules', version: '3.0.0', content: '' }] },
    };
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    expect(composition.final).toEqual([
      { slug: 'rules', version: '3.0.0', origin: 'seat', pinnedAt: null, overridden: false },
    ]);
  });

  it('records a pin as the version in effect and the scope that pinned it', () => {
    const overlays = withOps('room', [{ kind: 'pin', slug: 'rules', version: '1.2.0', content: '' }]);
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    expect(composition.final[0]).toEqual({
      slug: 'rules',
      version: '1.2.0',
      origin: 'seat-type',
      pinnedAt: 'room',
      overridden: false,
    });
  });

  it('marks an override without changing presence or version', () => {
    const overlays = withOps('company', [{ kind: 'override', slug: 'rules', version: '', content: 'edited' }]);
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    expect(composition.final[0]).toEqual({
      slug: 'rules',
      version: '1.0.0',
      origin: 'seat-type',
      pinnedAt: null,
      overridden: true,
    });
  });

  it('names a slug only an op mentions, so an impossible removal is still visible', () => {
    const overlays = withOps('seat', [{ kind: 'remove', slug: 'ghost', version: '', content: '' }]);
    const composition = composeBlocks([{ slug: 'rules', version: '1.0.0' }], overlays);

    expect(composition.known).toEqual(['ghost', 'rules']);
    expect(blocksAtScope(composition, 'seat').find((b) => b.slug === 'ghost')?.present).toBe(false);
  });
});

describe('removalOutcome', () => {
  it('says a block inherited from above stays defined there', () => {
    const overlays = withOps('company', [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }]);
    const outcome = removalOutcome(entry(overlays, 'seat', 'style'), 'seat');

    expect(outcome).toEqual({
      allowed: true,
      label: 'removed at seat · still defined at company',
    });
  });

  it('says a block this level added is its only definition', () => {
    const overlays = withOps('seat', [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }]);
    const outcome = removalOutcome(entry(overlays, 'seat', 'style'), 'seat');

    expect(outcome).toEqual({
      allowed: true,
      label: 'removed at seat; this level is the only definition',
    });
  });

  it('refuses a removal of a block that is not in effect here, with the resolver reason', () => {
    const overlays = withOps('seat', [{ kind: 'remove', slug: 'rules', version: '', content: '' }]);
    const outcome = removalOutcome(entry(overlays, 'seat', 'rules'), 'seat');

    expect(outcome.allowed).toBe(false);
    expect(outcome.reason).toBe('already removed at seat: the resolver refuses a second remove');
  });

  it('does NOT refuse a removal of a pinned block - the resolver has no pin lock', () => {
    const overlays = withOps('company', [{ kind: 'pin', slug: 'rules', version: '1.2.0', content: '' }]);
    const row = entry(overlays, 'seat', 'rules');

    expect(row.block?.pinnedAt).toBe('company');
    expect(removalOutcome(row, 'seat').allowed).toBe(true);
  });
});

describe('additionOutcome', () => {
  it('allows adding a block that is not in effect at this level', () => {
    const overlays = withOps('seat', [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }]);

    // 'style' is known from the seat op but has not applied yet at the company level.
    expect(additionOutcome(entry(overlays, 'company', 'style'), 'company')).toEqual({
      allowed: true,
      label: 'added at company',
    });
  });

  it('refuses adding a block already in effect, with the resolver reason', () => {
    expect(additionOutcome(entry(emptyOverlays(), 'seat', 'rules'), 'seat')).toEqual({
      allowed: false,
      reason: 'already in effect at seat: the resolver refuses a second add',
    });
  });
});

describe('op helpers', () => {
  const add: SeatOverlayOp = { kind: 'add', slug: 'style', version: '2.0.0', content: '' };
  const remove: SeatOverlayOp = { kind: 'remove', slug: 'style', version: '', content: '' };

  it('appends one add op', () => {
    expect(withAddedBlock([], 'style', '2.0.0')).toEqual([add]);
  });

  it('undoes a removal by dropping this scope add rather than writing a second op', () => {
    expect(withRemovedBlock([add], 'style')).toEqual([]);
  });

  it('removes an inherited block by appending a remove op', () => {
    expect(withRemovedBlock([], 'style')).toEqual([remove]);
  });

  it('restores by dropping this scope remove op', () => {
    expect(withRestoredBlock([remove], 'style')).toEqual([]);
  });
});

describe('originLabel', () => {
  it('reads the seat type as a phrase and the scopes as themselves', () => {
    expect(originLabel('seat-type')).toBe('the seat type');
    expect(originLabel('room')).toBe('room');
  });
});
