/**
 * Session API - the signed-in user's connector sessions.
 *
 * Route (agenthub_go/fastmcp/server/httpapp/session_stream_routes.go):
 *   GET /api/v2/sessions -> { sessions: SessionSummary[] }
 *
 * Bearer-authenticated and filtered to the calling user by the server, so no
 * user id is sent. The live view does not use
 * GET /api/v2/sessions/{id}/events: the server pages that route oldest-first,
 * while useSessionStream replays every stored event over the socket before
 * following the live ones.
 *
 * @module services/sessionApi
 * @version 1.0.0
 */

import { apiRequest } from './apiV2';
import type { SessionsResponse } from '../types/sessionTypes';

const SESSIONS = '/api/v2/sessions';

export const sessionApi = {
  /** Sessions for the signed-in user, newest activity first. */
  listSessions: () => apiRequest<SessionsResponse>(SESSIONS),
};
