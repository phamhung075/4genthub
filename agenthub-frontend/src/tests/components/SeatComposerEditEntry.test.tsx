/**
 * @fileoverview The composer's edit entry point: WHICH block it hands out, and that it is opt-in.
 *
 * WHY THE VERSION IS THE CASE THAT MATTERS. A composed block holds the version IN EFFECT at the
 * level being viewed, while the modules list carries each module's LATEST published version - so a
 * row can render `1.0.0` while the list says `2.0.0`, which is exactly what a pinned block or a
 * seat type pinned to an older version looks like. An edit that carried the list's version would
 * prefill the form from a tree the user is not looking at and then publish over it, so the fixture
 * is built with the list AHEAD of the refs and the case cannot pass on that mistake.
 */

import React from 'react';
import { vi } from 'vitest';
import { fireEvent, render, screen } from '../test-utils';
import { SeatComposer } from '../../components/seats/SeatComposer';
import type { ModuleSummary, SeatType } from '../../types/seatTypes';

/** Two refs the modules list carries at a LATER version, and one it does not carry at all. */
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
      { slug: 'legacy-block', version: '1.0.0' },
    ],
  } as unknown as SeatType,
  modules: [
    { slug: 'guide-web-dev', kind: 'instruction', version: '2.0.0', sha256: 'a' },
    { slug: 'policy-web-dev', kind: 'policy', version: '3.0.0', sha256: 'b' },
  ] as unknown as ModuleSummary[],
  overlays: {},
  isSaving: false,
  saveError: null,
  onApply: vi.fn(),
});

describe('the composer edit entry point', () => {
  it('hands out the version the row SHOWS and the kind the list carries, decided per row', () => {
    const onEditBlock = vi.fn();
    render(<SeatComposer {...composerFixture()} onEditBlock={onEditBlock} />);

    fireEvent.click(screen.getByRole('button', { name: 'Edit and publish block guide-web-dev@1.0.0' }));
    expect(onEditBlock).toHaveBeenLastCalledWith({
      slug: 'guide-web-dev',
      // The ref in effect, NOT the 2.0.0 the modules list carries: an edit publishes from what the
      // row shows.
      version: '1.0.0',
      kind: 'instruction',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Edit and publish block policy-web-dev@1.0.0' }));
    expect(onEditBlock).toHaveBeenLastCalledWith({
      slug: 'policy-web-dev',
      version: '1.0.0',
      // Looked up per slug rather than hardcoded for the whole list.
      kind: 'policy',
    });
    expect(onEditBlock).toHaveBeenCalledTimes(2);
  });

  it('offers nothing for a slug the modules list does not carry, because there is no kind to publish with', () => {
    const onEditBlock = vi.fn();
    render(<SeatComposer {...composerFixture()} onEditBlock={onEditBlock} />);

    // The row itself still renders - a block whose kind the list lacks falls back to Guide - and
    // only the affordance is withheld, rather than offering one that opens a form it cannot fill.
    expect(screen.getByText('legacy-block@1.0.0')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /edit and publish block legacy-block/i })
    ).toBeNull();
    expect(onEditBlock).not.toHaveBeenCalled();
  });

  it('renders no affordance for a caller that does not ask for one', () => {
    render(<SeatComposer {...composerFixture()} />);

    // The other reader is the seat-detail page, which passes no callback: its rows must be exactly
    // the rows they were, so the removal affordance is the control for this case - one per row,
    // and no edit button anywhere.
    expect(screen.queryByRole('button', { name: /edit and publish/i })).toBeNull();
    expect(screen.getAllByRole('button', { name: /remove here/i })).toHaveLength(3);
  });
});
