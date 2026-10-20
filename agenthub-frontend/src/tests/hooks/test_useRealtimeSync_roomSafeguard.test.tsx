/**
 * Tests for the safeguard alert consumer (payload.entity 'room_safeguard').
 *
 * The frame shape is the one `routes.BroadcastDataChange` produces for 7.3's producers
 * (`raiseRoomSafeguardAlert`, `raiseAgentDeadmanAlert` in
 * agenthub_go/fastmcp/server/httpapp/ws_connector_safeguard.go): type 'update', entity
 * 'room_safeguard', action 'safeguard_alert', data.primary carrying the row's own fields,
 * metadata.entity_id the row key and metadata.event_type 'safeguard_alert'.
 *
 * Before this consumer existed the frame fell to the dispatcher's default branch, so an owner was
 * alerted about a stopped safeguard or a silent machine by a frame the dashboard logged at debug
 * level and showed nowhere.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, renderHook, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { useNotificationStore } from '../../store/notifications';
import { NotificationBell } from '../../components/NotificationBell';
import logger from '../../utils/logger';
import type { WSMessage } from '../../types/websocketTypes';

const showInfo = vi.fn();
const showWarning = vi.fn();
const showSuccess = vi.fn();

vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => showSuccess,
  useInfoToast: () => showInfo,
  useWarningToast: () => showWarning,
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

type WsHandler = (msg: WSMessage) => void;

/**
 * One alert frame. `frameId` is the frame's own id, which is what the consumer dedupes on, and
 * `entityId` is the row key, which repeats across the row's life - a second alert about the same
 * row carries the same entity_id and a new frame id.
 */
const safeguardAlertFrame = (primary: Record<string, unknown>, frameId: string, entityId: string): WSMessage =>
  ({
    id: frameId,
    version: '2.0',
    type: 'update',
    timestamp: new Date().toISOString(),
    sequence: 4242,
    payload: {
      entity: 'room_safeguard',
      action: 'safeguard_alert',
      data: { primary },
    },
    metadata: {
      source: 'system',
      userId: 'dev-user-001',
      entity_type: 'room_safeguard',
      entity_id: entityId,
      event_type: 'safeguard_alert',
    },
  }) as unknown as WSMessage;

describe('useRealtimeSync - safeguard alerts', () => {
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

  it('stores the row the alert names, with its counters, and toasts it once', () => {
    const send = renderAndCapture();

    send(
      safeguardAlertFrame(
        { connector_id: 'conn-1', room: 'demo', safeguard: 'compact', state: 'failing', restarts: 3, age_s: 41 },
        'broadcast-room_safeguard-100001',
        'conn-1/demo/compact'
      )
    );

    const state = useNotificationStore.getState();
    expect(state.notifications).toHaveLength(1);
    expect(state.notifications[0]).toMatchObject({
      id: 'broadcast-room_safeguard-100001',
      message: 'Safeguard compact (room demo, connector conn-1) is failing (3 restarts, last beat 41s ago)',
      kind: 'safeguard_alert',
      read: false,
    });
    expect(state.unreadCount).toBe(1);
    expect(showWarning).toHaveBeenCalledTimes(1);
    expect(showWarning).toHaveBeenCalledWith(
      'Safeguard compact (room demo, connector conn-1) is failing (3 restarts, last beat 41s ago)'
    );
  });

  it('reads the dead-man frame as unreachable rather than inventing a state', () => {
    const send = renderAndCapture();

    send(safeguardAlertFrame({ connector_id: 'conn-1', safeguard: 'agent' }, 'broadcast-room_safeguard-100002', 'conn-1/agent'));

    expect(useNotificationStore.getState().notifications[0].message).toBe(
      'Safeguard agent (connector conn-1) is unreachable: the connector stayed offline past its heartbeat close'
    );
  });

  it('keeps a replayed frame as one inbox row and does not toast it twice', () => {
    const send = renderAndCapture();
    const frame = safeguardAlertFrame(
      { connector_id: 'conn-1', room: 'demo', safeguard: 'watchdog', state: 'silent', age_s: 200 },
      'broadcast-room_safeguard-100003',
      'conn-1/demo/watchdog'
    );

    send(frame);
    send(frame);

    expect(useNotificationStore.getState().notifications).toHaveLength(1);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
    expect(showWarning).toHaveBeenCalledTimes(1);
  });

  it('a second alert about the same row is a second inbox row', () => {
    const send = renderAndCapture();

    send(
      safeguardAlertFrame(
        { connector_id: 'conn-1', room: 'demo', safeguard: 'compact', state: 'stopped', age_s: 12 },
        'broadcast-room_safeguard-100004',
        'conn-1/demo/compact'
      )
    );
    send(
      safeguardAlertFrame(
        { connector_id: 'conn-1', room: 'demo', safeguard: 'compact', state: 'stopped', age_s: 13 },
        'broadcast-room_safeguard-100005',
        'conn-1/demo/compact'
      )
    );

    const state = useNotificationStore.getState();
    expect(state.notifications).toHaveLength(2);
    expect(state.unreadCount).toBe(2);
  });

  it('drops a frame that names no safeguard, and says so', () => {
    const send = renderAndCapture();

    send(safeguardAlertFrame({ connector_id: 'conn-1', state: 'stopped' }, 'broadcast-room_safeguard-100006', 'conn-1'));

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
    expect(logger.warn).toHaveBeenCalledWith('[useRealtimeSync] Safeguard alert frame without a safeguard name');
  });

  it('the inbox shows the alert and counts it unread', () => {
    const send = renderAndCapture();

    send(
      safeguardAlertFrame(
        { connector_id: 'conn-1', room: 'demo', safeguard: 'roomguard', state: 'silent', restarts: 1, age_s: 95 },
        'broadcast-room_safeguard-100007',
        'conn-1/demo/roomguard'
      )
    );

    render(<NotificationBell />, { wrapper: createWrapper() });

    expect(screen.getByTestId('notification-unread-count')).toHaveTextContent('1');

    fireEvent.click(screen.getByLabelText('Notifications (1 unread)'));

    expect(screen.getByTestId('notification-inbox')).toHaveTextContent(
      'Safeguard roomguard (room demo, connector conn-1) is silent (1 restarts, last beat 95s ago)'
    );
  });
});
