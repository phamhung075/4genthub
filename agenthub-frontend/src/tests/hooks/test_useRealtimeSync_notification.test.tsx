/**
 * Tests for the dashboard push consumer (payload.entity 'notification').
 *
 * The frame shape is the one the server produced for POST /api/v2/broadcast/notify on a local
 * build: type 'update', entity 'notification', action 'notification', data.primary copied from
 * the request, metadata.entity_id carrying the message id. These fail if the dispatcher loses
 * the notification case - the frame would fall to the default branch and the store would stay
 * empty.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { useNotificationStore } from '../../store/notifications';
import type { WSMessage } from '../../types/websocketTypes';

vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

type WsHandler = (msg: WSMessage) => void;

const notificationFrame = (overrides: { id?: string; message?: string; from?: string } = {}): WSMessage => ({
  id: 'broadcast-notification-1',
  version: '2.0',
  type: 'update',
  timestamp: new Date().toISOString(),
  sequence: 1,
  payload: {
    entity: 'notification',
    action: 'notification',
    data: {
      primary: {
        message: overrides.message ?? 'hello from alice',
        from: overrides.from ?? 'alice',
        room: 'demo',
        seat: 'alice',
        kind: 'agent_message',
      },
    },
  },
  metadata: {
    source: 'system',
    userId: 'dev-user-001',
    entity_type: 'notification',
    entity_id: overrides.id ?? 'msg-1',
    event_type: 'notification',
  },
});

describe('useRealtimeSync - dashboard notifications', () => {
  let queryClient: QueryClient;
  let messageHandler: WsHandler | null;
  let mockWebSocketClient: { on: (event: string, handler: WsHandler) => void; off: () => void; isConnected: boolean };

  beforeEach(() => {
    vi.clearAllMocks();
    messageHandler = null;
    useNotificationStore.getState().reset();

    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

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
    useNotificationStore.getState().reset();
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

  it('stores a notification frame and counts it unread', () => {
    const send = renderAndCapture();

    send(notificationFrame());

    const state = useNotificationStore.getState();
    expect(state.notifications).toHaveLength(1);
    expect(state.notifications[0]).toMatchObject({
      id: 'msg-1',
      message: 'hello from alice',
      from: 'alice',
      room: 'demo',
      seat: 'alice',
      kind: 'agent_message',
      read: false,
    });
    expect(state.unreadCount).toBe(1);
  });

  it('ignores a notification frame without a message', () => {
    const send = renderAndCapture();

    send({
      ...notificationFrame(),
      payload: { entity: 'notification', action: 'notification', data: { primary: {} } },
    } as WSMessage);

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });

  it('dedupes a replayed frame with the same id', () => {
    const send = renderAndCapture();

    send(notificationFrame());
    send(notificationFrame());

    expect(useNotificationStore.getState().notifications).toHaveLength(1);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
  });
});
