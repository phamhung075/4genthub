/**
 * @fileoverview The composer's five purposes: the mirror, the two naming families, and the view.
 *
 * WHY THE FIRST CASE READS GO SOURCE RATHER THAN A FRONTEND CONSTANT. `types/seatTypes.ts` used to
 * say its kind list "mirrors resolver.ModuleKind" while it had silently drifted by one kind
 * (`policy` existed in Go and in the seeded team files, and not in the list the publish form renders
 * from). A comment that mirrors is a claim; a test that reads BOTH sides is a check. This case
 * therefore opens `agenthub_go/.../resolver/resolver.go` and compares the literals there with
 * `SEAT_MODULE_KINDS`, so it fails when EITHER side gains or loses a kind.
 *
 * IT REQUIRES THE GO TREE and fails rather than skips when the file cannot be read, because a mirror
 * check that cannot see the other side proves nothing at all.
 */

import fs from 'node:fs';
import path from 'node:path';
import React from 'react';
import { vi } from 'vitest';
import { render, screen } from '../test-utils';
import { SEAT_MODULE_KINDS, type ModuleSummary, type SeatType } from '../../types/seatTypes';
import {
  BLOCK_PURPOSES,
  PURPOSE_LABEL,
  SeatComposer,
  kindsOfPurpose,
  purposeOf,
} from '../../components/seats/SeatComposer';

/** A seat whose three blocks exercise the grouping: two kinds that own a purpose, one family slug. */
const composerFixture = (): React.ComponentProps<typeof SeatComposer> => ({
  room: '4genthub-min',
  seat: 'web-dev',
  seatType: {
    slug: 'dev',
    name: 'Dev',
    description: 'Builds the app',
    default_runtime: 'omp',
    latest_version: '1.0.0',
    module_refs: [
      { slug: 'guide-web-dev', version: '1.0.0' },
      { slug: 'policy-web-dev', version: '1.0.0' },
      { slug: 'mcp-usage', version: '1.0.0' },
    ],
  } as unknown as SeatType,
  modules: [
    { slug: 'guide-web-dev', kind: 'instruction', version: '1.0.0', sha256: 'a' },
    { slug: 'policy-web-dev', kind: 'policy', version: '1.0.0', sha256: 'b' },
    { slug: 'mcp-usage', kind: 'instruction', version: '1.0.0', sha256: 'c' },
  ] as unknown as ModuleSummary[],
  overlays: {},
  isSaving: false,
  saveError: null,
  onApply: vi.fn(),
});

const RESOLVER_SOURCE = path.resolve(
  process.cwd(),
  '..',
  'agenthub_go/fastmcp/seat_management/domain/resolver/resolver.go'
);

/** The kind literals the Go resolver declares, in source order. */
function kindsFromResolverSource(): string[] {
  const text = fs.readFileSync(RESOLVER_SOURCE, 'utf8');
  return [...text.matchAll(/Kind\w+\s+ModuleKind\s*=\s*"([a-z]+)"/g)].map(match => match[1]);
}

describe('the composer purposes', () => {
  it('mirrors the kinds the Go resolver accepts, and gives each kind exactly one purpose', () => {
    const goKinds = kindsFromResolverSource();

    // The read worked at all - an empty read would make the comparison below vacuous.
    expect(goKinds.length).toBeGreaterThan(0);
    // The mirror, in BOTH directions: a kind added in Go fails here, and so does one dropped here.
    expect([...SEAT_MODULE_KINDS].sort()).toEqual([...goKinds].sort());

    const owned = BLOCK_PURPOSES.flatMap(purpose => kindsOfPurpose(purpose));
    // Every kind has a purpose, so no kind can vanish from the view...
    expect([...owned].sort()).toEqual([...SEAT_MODULE_KINDS].sort());
    // ...and none has two, so no block can be rendered twice.
    expect(new Set(owned).size).toBe(owned.length);
  });

  it('files the two naming families under Tools/MCP, and only those', () => {
    // `mcp-usage` is KindInstruction while its own comment calls it the seat's MCP guidance;
    // `delegate-deepseek` is KindInstruction while it tells a seat to use the deepseek tool.
    expect(purposeOf('mcp-usage', 'instruction')).toBe('tools-mcp');
    expect(purposeOf('delegate-deepseek', 'instruction')).toBe('tools-mcp');
    // The override is discriminating rather than a rule that swallows every instruction block.
    expect(purposeOf('guide-web-dev', 'instruction')).toBe('guide');
    // And a kind that already owns a purpose is untouched by the families.
    expect(purposeOf('policy-web-dev', 'policy')).toBe('policy');
  });

  it('renders every purpose in order, each block under its purpose, with its own empty state', () => {
    render(<SeatComposer {...composerFixture()} />);

    const list = screen.getByRole('list', { name: 'Composed blocks' });
    const text = list.textContent ?? '';

    // Fixed order, asserted by position rather than by presence.
    const positions = BLOCK_PURPOSES.map(purpose => text.indexOf(PURPOSE_LABEL[purpose]));
    expect(positions.every(position => position >= 0)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);

    // Each block sits under its own purpose: a policy block under Policy, and an INSTRUCTION block
    // whose slug is in the mcp- family under Tools/MCP rather than under Guide.
    const policy = text.indexOf(PURPOSE_LABEL.policy);
    const tools = text.indexOf(PURPOSE_LABEL['tools-mcp']);
    const skills = text.indexOf(PURPOSE_LABEL.skills);
    expect(text.indexOf('policy-web-dev')).toBeGreaterThan(policy);
    expect(text.indexOf('policy-web-dev')).toBeLessThan(tools);
    expect(text.indexOf('mcp-usage')).toBeGreaterThan(tools);
    expect(text.indexOf('mcp-usage')).toBeLessThan(skills);

    // An empty purpose shows its own empty state rather than an empty section.
    expect(text).toContain('No Skills blocks at this level.');
  });
});
