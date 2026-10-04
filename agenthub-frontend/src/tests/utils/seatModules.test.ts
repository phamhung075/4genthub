import { describe, expect, it } from 'vitest';
import { computeEffectiveModules } from '../../lib/seatModules';
import type { SeatOverlay, SeatOverlayOp, SeatOverlays } from '../../types/seatTypes';

const overlay = (scope: SeatOverlay['scope'], ops: SeatOverlayOp[] = []): SeatOverlay => ({ scope, ops });
const overlays = (company: SeatOverlayOp[] = [], room: SeatOverlayOp[] = [], seat: SeatOverlayOp[] = []): SeatOverlays => ({
  company: overlay('company', company),
  room: overlay('room', room),
  seat: overlay('seat', seat),
});
const op = (kind: SeatOverlayOp['kind'], slug: string, version = '', content = ''): SeatOverlayOp => ({
  kind,
  slug,
  version,
  content,
});

describe('computeEffectiveModules', () => {
  const refs = [
    { slug: 'rules', version: '1.0.0' },
    { slug: 'tools', version: '2.1.0' },
  ];

  it('returns the seat type refs with their versions when no overlay applies', () => {
    const result = computeEffectiveModules(refs, overlays());

    expect(result.map(m => [m.slug, m.version, m.removed, m.overridden])).toEqual([
      ['rules', '1.0.0', false, false],
      ['tools', '2.1.0', false, false],
    ]);
  });

  it('applies add and pin versions in company, room, seat order', () => {
    const result = computeEffectiveModules(
      refs,
      overlays([op('add', 'extra', '1.0.0')], [op('pin', 'rules', '1.5.0')], [op('pin', 'extra', '1.2.0')])
    );

    const byslug = Object.fromEntries(result.map(m => [m.slug, m]));
    expect(byslug.rules.version).toBe('1.5.0');
    expect(byslug.extra.version).toBe('1.2.0');
    expect(byslug.extra.changes).toEqual([
      { scope: 'company', kind: 'add' },
      { scope: 'seat', kind: 'pin' },
    ]);
  });

  it('marks a removed module and brings it back when it is added again', () => {
    const removed = computeEffectiveModules(refs, overlays([], [op('remove', 'tools')]));
    expect(removed.find(m => m.slug === 'tools')?.removed).toBe(true);

    const readded = computeEffectiveModules(refs, overlays([], [op('remove', 'tools')], [op('add', 'tools', '3.0.0')]));
    const tools = readded.find(m => m.slug === 'tools');
    expect(tools?.removed).toBe(false);
    expect(tools?.version).toBe('3.0.0');
  });

  it('keeps the content of an override and flags the module', () => {
    const result = computeEffectiveModules(refs, overlays([], [], [op('override', 'rules', '', 'custom rules')]));

    const rules = result.find(m => m.slug === 'rules');
    expect(rules).toMatchObject({ overridden: true, contentOverride: 'custom rules', version: '1.0.0' });
  });

  it('has no version for a module that no ref or add op gives one', () => {
    const result = computeEffectiveModules([], overlays([], [], [op('override', 'orphan', '', 'text')]));

    expect(result.find(m => m.slug === 'orphan')?.version).toBe('');
  });
});
