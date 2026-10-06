/**
 * Friction channel API - the read side of Directive H.
 *
 * ONE ROUTE, AND NO PARAMETERS: `GET /api/v2/openrig/feedback`. The contract states
 * there is no layer filter, no limit and no cursor in this cut - deliberately, because
 * the grouping is the deliverable and a filter invites one layer to read as the whole
 * set. Nothing is added here to compensate.
 *
 * The two submission paths (a shell command and an MCP tool) belong to the backend and
 * have no client in this file; this module must not grow one.
 *
 * @module services/feedbackApi
 * @version 1.0.0
 */

import { apiRequest } from './apiV2';
import type { FeedbackListResponse } from '../types/feedback';

const OPENRIG = '/api/v2/openrig';

export const feedbackApi = {
  /**
   * Every friction report the caller may see: the route is tenant-scoped by the caller's
   * user id, and a machine token does not authenticate on it at all.
   */
  listFeedback: () => apiRequest<FeedbackListResponse>(`${OPENRIG}/feedback`),
};
