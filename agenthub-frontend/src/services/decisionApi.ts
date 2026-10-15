/**
 * Decision API - the owner's side of a room lead's ask.
 *
 * The cloud row is a projection of the local queue row: the daemon mirrors the ask up, the owner
 * answers here, and the daemon pulls the answer down and applies it. Two consequences the callers
 * must respect, both from the frozen contract of 2026-10-12 (lane 1):
 *
 * - `answered` is NOT closure. The row stays in the room's open list ("awaiting the room") until
 *   the daemon applies the answer and pushes `resolved` (or `superseded`, if it was answered
 *   elsewhere first).
 * - One click per call: the server validates the option against the stored questions and refuses
 *   an unknown one (`422`), a row that is not `pending` (`409`) and a caller that is not the asked
 *   human (`403`). Those refusals are rendered, never retried blindly.
 *
 * @module services/decisionApi
 */

import { apiRequest } from './apiV2';
import type {
  AnswerRoomDecisionRequest,
  AnswerRoomDecisionResponse,
  RoomDecisionsResponse,
} from '../types/seatTypes';

/**
 * The room's decision rows: `/api/v2/rooms/{room}/decisions`, the route
 * `agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go` mounts. The prefix was
 * `/api/v2/openrig` while the legacy rig client owned the routes; `cbc51bae` ("purge
 * the legacy rig client; client routes move to /api/v2") moved them and deleted the old
 * mount, so the openrig spelling answered 404 and the panel could only ever render a
 * failed read.
 */
const decisionsPath = (room: string) => `/api/v2/rooms/${encodeURIComponent(room)}/decisions`;

export const decisionApi = {
  /** The room's open asks - `pending` and `answered`, tenant- and room-scoped server-side. */
  listRoomDecisions: (room: string) =>
    apiRequest<RoomDecisionsResponse>(decisionsPath(room)),

  /** Record one question's choice. Returns `{state, answers, complete}` as the daemon records it. */
  answerRoomDecision: (room: string, decisionId: string, body: AnswerRoomDecisionRequest) =>
    apiRequest<AnswerRoomDecisionResponse>(
      `${decisionsPath(room)}/${encodeURIComponent(decisionId)}/answer`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    ),
};
