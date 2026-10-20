/**
 * Decision API - the owner's side of a room lead's ask.
 *
 * The cloud row is a projection of the local queue row: the room's daemon mirrors the ask up, the
 * owner answers here, and the daemon pulls the answer down and applies it. Two consequences the
 * callers must respect, both from the room decision channel's own contract
 * (`agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go`):
 *
 * - `answered` is NOT closure. The row stays in the room's list ("awaiting the room") until the
 *   daemon applies the answer and pushes `resolved` (or `superseded`, if it was answered elsewhere
 *   first).
 * - One click per call: the server validates the option against the stored questions and refuses an
 *   unknown one (`422`), a row that is not `pending` (`409`) and a caller that is not the asked
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
 * The room family's own prefix (`/api/v2/rooms`, the root the seat and rigspec routes serve):
 * `{room}` is the SLUG. The transport's file header names a second prefix for one entity as a
 * second way to name a room, so this client adds none.
 */
const decisionsPath = (room: string) => `/api/v2/rooms/${encodeURIComponent(room)}/decisions`;

export const decisionApi = {
  /** The room's asks - scoped server-side to the caller's tenant, so a viewer reads an empty list. */
  listRoomDecisions: (room: string) => apiRequest<RoomDecisionsResponse>(decisionsPath(room)),

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
