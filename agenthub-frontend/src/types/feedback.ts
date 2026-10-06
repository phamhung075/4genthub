/**
 * Friction channel types - the read side of the seat friction channel (Directive H).
 *
 * THE WIRE SHAPE HERE IS THE BACKEND OWNER'S STATED CONTRACT (go-dev, 2026-10-06), not a
 * guess: the response is already grouped by layer, every key of a row is always present
 * and an empty string is used where a value is unknown - never JSON null. The layer is a
 * CLOSED SET fixed by the backend's CHECK constraint, so it is a union here: a value
 * outside it is a contract breach rather than a new category.
 *
 * @module types/feedback
 * @version 1.0.0
 */

/** The layers a report can name, in the canonical order the backend sends and the page shows. */
export const FEEDBACK_LAYERS = [
  'runtime',
  'openrig',
  'cloud',
  'seat-context',
  'workspace',
  'other',
] as const;

export type FeedbackLayer = (typeof FEEDBACK_LAYERS)[number];

/** What each layer covers, as the directive that fixed the set words it. */
export const FEEDBACK_LAYER_MEANING: Record<FeedbackLayer, string> = {
  runtime: 'The agent runtime and harness: permissions, prompts, tool availability.',
  openrig: 'The rig CLI, the daemon, the seat lifecycle, tmux.',
  cloud: 'The platform API and the MCP surface: routes, auth, sync.',
  'seat-context': 'The rendered seat: role text, skills, overlays, blocks.',
  workspace: 'The repository and its tooling: tests, builds, editors.',
  other: 'Friction that belongs to none of the layers above.',
};

/**
 * One friction report. Every key is always present; an empty string is how the API says
 * "unknown", so `session` and `machine_id` being empty is information and not a gap.
 * There is no title and no summary - `text` is the whole report.
 */
export interface FeedbackReport {
  /** The row key to use. */
  id: string;
  /** Room slug the report was filed from. */
  room: string;
  /** Seat (member id) the report was filed from. */
  seat: string;
  /** Full session name, empty string when unknown. */
  session: string;
  layer: FeedbackLayer;
  /** 1..2000 characters, never empty. */
  text: string;
  /** Server clock, RFC 3339 UTC. */
  created_at: string;
  /** The submitting bridge; empty string means the row was not submitted through one. */
  machine_id: string;
}

/** One layer's group. Present in the response only when the layer has reports. */
export interface FeedbackLayerGroup {
  layer: FeedbackLayer;
  count: number;
  reports: FeedbackReport[];
}

/** The list envelope: rows counted across all groups, groups already in canonical order. */
export interface FeedbackListResponse {
  success: boolean;
  total: number;
  layers: FeedbackLayerGroup[];
}
