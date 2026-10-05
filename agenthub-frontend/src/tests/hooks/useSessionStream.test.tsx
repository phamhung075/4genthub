/**
 * @fileoverview useSessionStream follows /ws/sessions/{id}: it reconnects from
 * the last seq on a dropped socket and treats the server's 4004 close as final.
 */

import { act, renderHook } from '@testing-library/react';
import { useSessionStream } from '../../hooks/useSessions';

vi.mock('../../config/environment', () => ({
  WS_URL: 'ws://test',
  WS_MAX_RECONNECT_ATTEMPTS: 3,
  WS_RECONNECT_DELAY: 1000,
}));

class MockSocket {
  static instances: MockSocket[] = [];
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockSocket.instances.push(this);
  }
}

const frame = (seq: number, payload: unknown = { text: `event ${seq}` }): MessageEvent =>
  new MessageEvent('message', { data: JSON.stringify({ seq, type: 'message', payload, ts: null }) });

const close = (code: number, reason = ''): CloseEvent => new CloseEvent('close', { code, reason });

const setup = (id: string | null = 's1', token: string | null = 'tok') =>
  renderHook(({ sessionId, token: t }) => useSessionStream(sessionId, t), {
    initialProps: { sessionId: id, token },
  });

describe('useSessionStream', () => {
  beforeEach(() => {
    MockSocket.instances = [];
    vi.stubGlobal('WebSocket', MockSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('opens /ws/sessions/{id} with the encoded id, token and cursor', () => {
    const { unmount } = setup('session 7', 'tok en');

    expect(MockSocket.instances).toHaveLength(1);
    expect(MockSocket.instances[0].url).toBe(
      'ws://test/ws/sessions/session%207?token=tok%20en&after_seq=0'
    );

    unmount();
  });

  it('goes live on open and appends replayed frames once, in order', () => {
    const { result, unmount } = setup();
    const socket = MockSocket.instances[0];

    act(() => socket.onopen!(new Event('open')));
    expect(result.current.status).toBe('live');

    act(() => {
      socket.onmessage!(frame(1));
      socket.onmessage!(frame(2));
      socket.onmessage!(frame(2)); // reconnect/replay overlap must not duplicate
    });

    expect(result.current.events.map((event) => event.seq)).toEqual([1, 2]);

    unmount();
  });

  it('treats close 4004 as terminal: not-found, no reconnect', () => {
    const { result, unmount } = setup();

    act(() => MockSocket.instances[0].onclose!(close(4004, 'Session not found')));

    expect(result.current.status).toBe('not-found');
    expect(result.current.error).toBe('Session not found');
    expect(MockSocket.instances).toHaveLength(1);

    unmount();
  });

  it('reconnects from the last seq after a dropped socket', () => {
    vi.useFakeTimers();
    const { result, unmount } = setup();

    act(() => {
      MockSocket.instances[0].onopen!(new Event('open'));
      MockSocket.instances[0].onmessage!(frame(5));
    });

    act(() => MockSocket.instances[0].onclose!(close(1006, 'abnormal')));
    expect(result.current.status).toBe('reconnecting');

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockSocket.instances).toHaveLength(2);
    expect(MockSocket.instances[1].url).toContain('after_seq=5');

    unmount();
  });

  it('resets to idle and drops the old events when the session id clears', () => {
    const { result, rerender, unmount } = setup();

    act(() => {
      MockSocket.instances[0].onopen!(new Event('open'));
      MockSocket.instances[0].onmessage!(frame(1));
    });
    expect(result.current.events).toHaveLength(1);

    rerender({ sessionId: null, token: 'tok' });

    expect(result.current.status).toBe('idle');
    expect(result.current.events).toEqual([]);

    unmount();
  });
});
