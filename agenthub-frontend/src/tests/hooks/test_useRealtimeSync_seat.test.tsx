/**
 * Tests for useRealtimeSync seat/room handling (item 16).
 *
 * These fail if the dispatcher lacks the seat/room cases: an unmatched entity
 * falls through to the default branch, so nothing is invalidated or animated.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { MockInstance } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { animationFactory } from '../../services/AnimationFactory';
import type { WSMessage } from '../../types/websocketTypes';
import type { SeatEventPayload, RoomEventPayload } from '../../types/websocket-protocol';

vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

type WsHandler = (msg: WSMessage) => void;

const seatMessage = (
  action: 'created' | 'updated' | 'deleted',
  primary: SeatEventPayload
): WSMessage => ({
  id: `msg-seat-${action}`,
  version: '2.0',
  type: 'update',
  timestamp: new Date().toISOString(),
  sequence: 1,
  payload: { entity: 'seat', action, data: { primary } },
  metadata: { source: 'user', userId: 'user-1' },
});

const roomMessage = (
  action: 'created' | 'updated' | 'deleted',
  primary: RoomEventPayload
): WSMessage => ({
  id: `msg-room-${action}`,
  version: '2.0',
  type: 'update',
  timestamp: new Date().toISOString(),
  sequence: 1,
  payload: { entity: 'room', action, data: { primary } },
  metadata: { source: 'user', userId: 'user-1' },
});

describe('useRealtimeSync - seat/room events', () => {
  let queryClient: QueryClient;
  let messageHandler: WsHandler | null;
  let mockWebSocketClient: { on: (event: string, handler: WsHandler) => void; off: () => void; isConnected: boolean };
  let invalidateSpy: MockInstance;
  let removeSpy: MockInstance;

  beforeEach(() => {
    vi.clearAllMocks();
    messageHandler = null;

    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    removeSpy = vi.spyOn(queryClient, 'removeQueries');

    mockWebSocketClient = {
      on: vi.fn((event: string, handler: WsHandler) => {
        if (event === 'update') {
          messageHandler = handler;
        }
      }),
      off: vi.fn(),
      isConnected: true,
    };
  });

  afterEach(() => {
    queryClient.clear();
  });

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  const renderAndCapture = () => {
    renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper: createWrapper() });
    if (!messageHandler) {
      throw new Error('WebSocket handler was not registered');
    }
    return messageHandler;
  };

  it('invalidates the seat keys and animates the row on a seat created event', () => {
    const send = renderAndCapture();

    send(seatMessage('created', { id: 'dev/alice', room: 'dev', seat_key: 'alice' }));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatSeats', 'dev'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatRooms'] });
    expect(animationFactory.animate).toHaveBeenCalledWith('dev/alice', 'create', 'websocket');
  });

  it('invalidates the per-seat keys and animates on a seat updated event', () => {
    const send = renderAndCapture();

    send(seatMessage('updated', { id: 'dev/alice', room: 'dev', seat_key: 'alice' }));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatSeats', 'dev'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatOverlays', 'dev', 'alice'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatLinks', 'dev', 'alice'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatResolved', 'dev', 'alice'] });
    expect(animationFactory.animate).toHaveBeenCalledWith('dev/alice', 'update', 'websocket');
  });

  it('drops the per-seat caches and animates on a seat deleted event', () => {
    const send = renderAndCapture();

    send(seatMessage('deleted', { id: 'dev/alice', room: 'dev', seat_key: 'alice' }));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatSeats', 'dev'] });
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['seatOverlays', 'dev', 'alice'] });
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['seatLinks', 'dev', 'alice'] });
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['seatResolved', 'dev', 'alice'] });
    expect(animationFactory.animate).toHaveBeenCalledWith('dev/alice', 'delete', 'websocket');
  });

  it('ignores a seat event without a room or seat key', () => {
    const send = renderAndCapture();

    // Missing seat_key: the handler must not touch the cache.
    send({
      id: 'msg-bad',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 1,
      payload: { entity: 'seat', action: 'created', data: { primary: { id: 'dev/alice', room: 'dev' } } },
      metadata: { source: 'user', userId: 'user-1' },
    });

    expect(invalidateSpy).not.toHaveBeenCalled();
    expect(animationFactory.animate).not.toHaveBeenCalled();
  });

  it('invalidates the room keys on a room created event', () => {
    const send = renderAndCapture();

    send(roomMessage('created', { id: 'dev', room: 'dev', name: 'Dev' }));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatRooms'] });
  });

  it('treats a company room updated event as a settings and overlay refresh', () => {
    const send = renderAndCapture();

    send(roomMessage('updated', { id: 'company', room: 'company' }));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatSettings'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatOverlays'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['seatResolved'] });
  });
});
