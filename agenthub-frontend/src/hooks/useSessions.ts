/**
 * Session Hooks - the session list and the live session stream.
 *
 * The stream replays every stored event the server holds for the session before
 * following the live ones, so it is the only source the live view needs; the
 * REST events route is not used (it pages oldest-first).
 *
 * @module hooks/useSessions
 * @version 1.0.0
 */

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { sessionApi } from '../services/sessionApi';
import type { SessionEvent } from '../types/sessionTypes';
import { WS_MAX_RECONNECT_ATTEMPTS, WS_RECONNECT_DELAY, WS_URL } from '../config/environment';
import logger from '../utils/logger';

export const sessionKeys = {
  list: ['sessions'] as const,
};

/** Sessions for the signed-in user, newest activity first. */
export function useSessions() {
  const query = useQuery({
    queryKey: sessionKeys.list,
    queryFn: async () => {
      const response = await sessionApi.listSessions();
      return response.sessions ?? [];
    },
  });
  return {
    sessions: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/** The transport states the live view can be in. */
export type SessionStreamStatus =
  | 'idle'
  | 'connecting'
  | 'live'
  | 'reconnecting'
  | 'not-found'
  | 'closed'
  | 'error';

export interface SessionStreamState {
  events: SessionEvent[];
  status: SessionStreamStatus;
  error: string | null;
}

/** Bounded so a long-lived stream cannot grow memory without limit. */
const MAX_STREAM_EVENTS = 2000;

// One text frame is either a stored replay event or a live one; anything that is
// not an object with a numeric seq is ignored rather than rendered.
function parseFrame(raw: unknown): SessionEvent | null {
  if (typeof raw !== 'string') return null;
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (value === null || typeof value !== 'object') return null;
  const { seq, type, payload, ts } = value as Record<string, unknown>;
  if (typeof seq !== 'number') return null;
  return {
    seq,
    type: typeof type === 'string' && type !== '' ? type : 'message',
    payload,
    ts: typeof ts === 'string' ? ts : null,
  };
}

/**
 * Follow one session over /ws/sessions/{id}: replay from after_seq, then live.
 * A 4004 close is the server's "missing or not yours" and is terminal; other
 * failures retry with exponential backoff up to the configured attempt count.
 */
export function useSessionStream(sessionId: string | null, token: string | null): SessionStreamState {
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [status, setStatus] = useState<SessionStreamStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId || !token) {
      setEvents([]);
      setStatus('idle');
      setError(null);
      return;
    }

    let socket: WebSocket | null = null;
    let attempts = 0;
    let lastSeq = 0;
    let stopped = false;
    let retryTimer: NodeJS.Timeout | undefined;

    setEvents([]);
    setError(null);
    setStatus('connecting');

    const open = () => {
      if (stopped) return;
      const url =
        `${WS_URL}/ws/sessions/${encodeURIComponent(sessionId)}` +
        `?token=${encodeURIComponent(token)}&after_seq=${lastSeq}`;
      socket = new WebSocket(url);
      setStatus(attempts === 0 ? 'connecting' : 'reconnecting');

      socket.onopen = () => {
        attempts = 0;
        setError(null);
        setStatus('live');
      };

      socket.onmessage = (event) => {
        const parsed = parseFrame(event.data);
        // Replay and a reconnect can both re-deliver a seq; keep the first.
        if (!parsed || parsed.seq <= lastSeq) return;
        lastSeq = parsed.seq;
        setEvents((prev) => {
          const next = [...prev, parsed];
          return next.length > MAX_STREAM_EVENTS ? next.slice(-MAX_STREAM_EVENTS) : next;
        });
      };

      socket.onerror = () => {
        // The close event that follows carries the code and reason.
        logger.debug('[session-stream] socket error', { sessionId });
      };

      socket.onclose = (close) => {
        socket = null;
        if (stopped) return;
        if (close.code === 4004) {
          setStatus('not-found');
          setError('Session not found');
          return;
        }
        if (close.code === 1000) {
          setStatus('closed');
          return;
        }
        if (attempts >= WS_MAX_RECONNECT_ATTEMPTS) {
          setStatus('error');
          setError(close.reason || 'Session stream closed');
          return;
        }
        attempts += 1;
        setStatus('reconnecting');
        retryTimer = setTimeout(open, WS_RECONNECT_DELAY * 2 ** (attempts - 1));
      };
    };

    open();

    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [sessionId, token]);

  return { events, status, error };
}
