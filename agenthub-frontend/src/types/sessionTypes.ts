/**
 * Session stream types - the browser side of the connector session stream.
 *
 * These mirror the Go DTOs exactly: `sessionRow` in
 * agenthub_go/fastmcp/session_stream/repository.go (id, name, project, status,
 * connector_id, last_seq, created_at, last_seen) and the event map in
 * `ListEvents` (seq, type, payload, ts). The list response deliberately carries
 * no session_key or user_id.
 *
 * @module types/sessionTypes
 * @version 1.0.0
 */

/** One row of GET /api/v2/sessions. */
export interface SessionSummary {
  /** Stable server-assigned session id (used as the /ws/sessions/{id} path segment). */
  id: string;
  /** Human name the connector reported for the session. */
  name: string;
  /** Connector-reported project, null when the connector sent none. */
  project: string | null;
  /** 'active' while the connector is holding it, 'offline' after MarkOffline. */
  status: string;
  /** Id of the connector that registered the session. */
  connector_id: string;
  /** Highest event seq stored for the session. */
  last_seq: number;
  /** ISO timestamp of creation, null when the row predates ts tracking. */
  created_at: string | null;
  /** ISO timestamp of last activity; the list is ordered by it, newest first. */
  last_seen: string | null;
}

/** Body of GET /api/v2/sessions. */
export interface SessionsResponse {
  sessions: SessionSummary[];
}

/** One stored/live event of a session. */
export interface SessionEvent {
  /** Server-assigned, strictly increasing per session; the replay cursor. */
  seq: number;
  /** Connector-declared type ('message' when the connector sent none). */
  type: string;
  /** Arbitrary JSON the connector attached. */
  payload: unknown;
  /** ISO timestamp, null when the row predates ts tracking. */
  ts: string | null;
}
