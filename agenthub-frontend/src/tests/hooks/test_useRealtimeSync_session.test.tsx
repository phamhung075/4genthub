/**
 * Tests for useRealtimeSync `agent_session` handling: the RULED browser surface for a connector
 * session's state (rigd-boundaries.md 2.3a).
 *
 * These fail if the dispatcher lacks the `agent_session` case, because an unmatched entity falls
 * through the switch and nothing is invalidated - the same failure mode the seat/room cases pin.
 * The frame's `data` deliberately carries a row: the handler must NOT read it, because the ruling
 * keeps `GET /api/v2/sessions` as the single read path.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { MockInstance } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
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

const agentSessionMessage = (action: 'created' | 'updated' | 'deleted'): WSMessage => ({
  id: `msg-agent-session-${action}`,
  version: '2.0',
  type: 'update',
  timestamp: new Date().toISOString(),
  sequence: 1,
  payload: {
    entity: 'agent_session',
    action,
    data: { primary: { id: 'row-1', seat_state: 'stopped', status: 'active' } },
  },
  metadata: { source: 'user', userId: 'user-1' },
});

describe('useRealtimeSync - agent_session events', () => {
  let queryClient: QueryClient;
  let messageHandler: WsHandler | null;
  let mockWebSocketClient: {
    on: (event: string, handler: WsHandler) => void;
    off: () => void;
    isConnected: boolean;
  };
  let invalidateSpy: MockInstance;

  beforeEach(() => {
    vi.clearAllMocks();
    messageHandler = null;

    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

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

  it('invalidates the session list on a created, updated or deleted agent_session frame', () => {
    const send = renderAndCapture();

    // All three actions, because 2.3a rules the invalidation for each of them - `updated` is what a
    // seat_state change and MarkOffline use, and MarkOffline emits one frame per session.
    for (const action of ['created', 'updated', 'deleted'] as const) {
      invalidateSpy.mockClear();

      send(agentSessionMessage(action));

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['sessions'] });
    }
  });
});
