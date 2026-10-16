/**
 * Session API - the signed-in user's connector sessions.
 *
 * Route (agenthub_go/fastmcp/server/httpapp/session_stream_routes.go):
 *   GET /api/v2/sessions -> { sessions: SessionSummary[] }
 *
 *   GET /api/v2/sessions/{id}/events?before_seq=N&limit=M -> { events: SessionEvent[] }
 *
 * Bearer-authenticated and filtered to the calling user by the server, so no
 * user id is sent. The live view opens with the newest events over the socket
 * (useSessionStream, `tail`); the events route with `before_seq` is how it pages
 * older history on request: the newest M events before N, oldest first.
 *
 * @module services/sessionApi
 * @version 1.0.0
 */

import { apiRequest } from './apiV2';
import type { SessionEvent, SessionsResponse } from '../types/sessionTypes';

const SESSIONS = '/api/v2/sessions';

export const sessionApi = {
  /** Sessions for the signed-in user, newest activity first. */
  listSessions: () => apiRequest<SessionsResponse>(SESSIONS),
  /** The newest `limit` events of a session that lie before `beforeSeq`, oldest first. */
  listEventsBefore: (sessionId: string, beforeSeq: number, limit: number) =>
    apiRequest<{ events: SessionEvent[] }>(
      `${SESSIONS}/${encodeURIComponent(sessionId)}/events?before_seq=${beforeSeq}&limit=${limit}`,
    ),
};
