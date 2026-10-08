// REPRODUCTION for the owner's report: CREATE fires once (confirmed on screen), but an
// UPDATE does not animate - neither a title change nor a status change.
//
// WHY THIS FILE EXISTS RATHER THAN A CASE IN WebSocketAnimationService.test.ts: that
// suite replaces animationFactory.animate with vi.fn().mockReturnValue(true), so it can
// only prove the service CALLS it, never that the animation LANDS. The owner's bug is on
// the landing side, so this file runs the REAL factory with a REAL registered element
// and asserts the element's CSS class, which is the only thing a call cannot fake.
//
// setPublished: the harness auto-mocks the factory in src/setupTests.ts, so it is
// unmocked here on purpose.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.unmock('../../services/AnimationFactory');

import { animationFactory } from '../../services/AnimationFactory';
import { webSocketAnimationService } from '../../services/WebSocketAnimationService';
import type { WSMessage } from '../../types/websocket-protocol';

/** A row element that records the classes the factory adds, like a real <tr>. */
function makeRow(): HTMLElement {
  const el = document.createElement('tr');
  return el;
}

/** A minimal but real v2.0 message for a task. */
function taskMessage(action: string, primary: Record<string, unknown>): WSMessage {
  return {
    id: `msg-${action}-${Math.random()}`,
    version: '2.0',
    type: 'update',
    timestamp: new Date().toISOString(),
    sequence: 1,
    payload: {
      entity: 'task',
      action,
      data: { primary },
    },
    metadata: { source: 'mcp-ai' },
  } as unknown as WSMessage;
}

describe('a task UPDATE must animate (the owner report)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('applies the update class to a registered task row on an updated event', async () => {
    const id = 'task-update-1';
    const row = makeRow();
    animationFactory.registerElement(id, row, 'task');

    const service = webSocketAnimationService;
    service.handleWebSocketMessage(taskMessage('updated', { id, title: 'After', status: 'in_progress' }));

    // The service defers by rAF + 150ms "to ensure DOM is ready"; run both.
    await vi.advanceTimersByTimeAsync(200);

    // The class is the proof: a mocked factory can return true without ever adding it.
    expect(row.className).toContain('taskRowUpdateAnimation');
  });

  it('applies the complete class on a completed event (the status-change case)', async () => {
    const id = 'task-complete-1';
    const row = makeRow();
    animationFactory.registerElement(id, row, 'task');

    const service = webSocketAnimationService;
    service.handleWebSocketMessage(taskMessage('completed', { id, title: 'Done', status: 'done' }));

    await vi.advanceTimersByTimeAsync(200);

    expect(row.className).toContain('taskRowCompleteAnimation');
  });
});
