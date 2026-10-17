/**
 * @fileoverview SessionLiveView renders a thinking step that ends with the queue-row schema
 * (facts, rule, decision, next) as the four fields, with the raw thinking collapsed beneath, and
 * renders a step without them exactly as before - both cases in ONE render, so the schema branch
 * cannot pass by painting every thinking step.
 */

import React from 'react';
import { render, screen, within } from '../test-utils';
import { SessionLiveView } from '../../components/sessions/SessionLiveView';
import type { SessionEvent } from '../../types/sessionTypes';

const thinkingEvent = (seq: number, thinking: string): SessionEvent => ({
  seq,
  type: 'message',
  payload: {
    text: JSON.stringify({
      type: 'message',
      message: { role: 'assistant', content: [{ type: 'thinking', thinking }] },
    }),
  },
  ts: null,
});

const SCHEMA_STEP =
  'weighing the two shapes\nfacts: branch=main; commit=8e706e18\nrule: rows carry the four fields\ndecision: build the view now\nnext: render it, fe-dev';
const RAW_STEP = 'just reasoning, no fields here';

describe('SessionLiveView', () => {
  it('shows the four fields for a step that carries them, and keeps a step without them raw', () => {
    render(
      <SessionLiveView
        sessionName="dev"
        events={[thinkingEvent(1, SCHEMA_STEP), thinkingEvent(2, RAW_STEP)]}
        status="live"
        error={null}
        hasOlder={false}
        loadingOlder={false}
        onLoadOlder={vi.fn()}
      />,
    );

    const [schemaCard, rawCard] = screen.getAllByRole('listitem');

    // The fields, in the schema's pinned order, each with its own value.
    const schemaList = within(schemaCard).getByText('facts').closest('dl');
    expect(schemaList).not.toBeNull();
    expect(Array.from(schemaList!.querySelectorAll('dt')).map((node) => node.textContent)).toEqual([
      'facts',
      'rule',
      'decision',
      'next',
    ]);
    expect(Array.from(schemaList!.querySelectorAll('dd')).map((node) => node.textContent)).toEqual([
      'branch=main; commit=8e706e18',
      'rows carry the four fields',
      'build the view now',
      'render it, fe-dev',
    ]);

    // The raw thinking is beneath the schema and collapsed: the reasoning above the fields survives.
    const schemaDetails = within(schemaCard).getByText('Show reasoning').closest('details');
    expect(schemaDetails).not.toBeNull();
    expect(schemaDetails!.hasAttribute('open')).toBe(false);
    expect(within(schemaDetails!).getByText(/weighing the two shapes/)).toBeTruthy();

    // The control: no fields, no schema view - today's card with its collapsed reasoning.
    expect(within(rawCard).queryByText('facts')).toBeNull();
    expect(within(rawCard).queryByText('rule')).toBeNull();
    const rawDetails = within(rawCard).getByText('Show reasoning').closest('details');
    expect(rawDetails).not.toBeNull();
    expect(rawDetails!.hasAttribute('open')).toBe(false);
    expect(within(rawDetails!).getByText(RAW_STEP)).toBeTruthy();
  });
});
