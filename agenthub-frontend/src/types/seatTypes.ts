/**
 * Seat Types - Company-workplace seat model
 *
 * A room is a grouping of seats, a seat is a fixed role slot and the occupant
 * (runtime + model) is replaceable. Modules are additive blocks that a seat,
 * a room or the whole company can customize through an overlay.
 *
 * @module types/seatTypes
 * @version 1.0.0
 */

// =============================================================================
// Core entities
// =============================================================================

export type SeatRuntime = 'claude-code' | 'codex' | 'agy' | 'omp';

/** Single source of truth for the runtimes offered in the UI. */
export const SEAT_RUNTIMES: SeatRuntime[] = ['claude-code', 'codex', 'agy', 'omp'];

/** Single source of truth for the policies the server accepts (resolver.PermissionPolicies). */
export const SEAT_PERMISSION_POLICIES = ['locked', 'standard', 'open', 'yolo', 'none'] as const;
export type SeatPermissionPolicy = (typeof SEAT_PERMISSION_POLICIES)[number];

export type SeatModuleKind = 'instruction' | 'document' | 'skill' | 'tool' | 'mcp' | 'memory';

/** Single source of truth for the module kinds offered in the UI (mirrors resolver.ModuleKind). */
export const SEAT_MODULE_KINDS: SeatModuleKind[] = ['instruction', 'document', 'skill', 'tool', 'mcp', 'memory'];

/** The transports an mcp block distinguishes (mcpblock.TypeHTTP / TypeStdio). */
export const MCP_SERVER_TYPES = ['http', 'stdio'] as const;
export type McpServerType = (typeof MCP_SERVER_TYPES)[number];

/**
 * One whole MCP server as an mcp block's content describes it, matching the Go
 * `mcpblock.Server` field for field. A block mounts the server; per-tool
 * narrowing stays in the permission layer.
 */
export interface McpServerBlock {
  /** The server key in the rendered MCP fragment. */
  name: string;
  type: McpServerType;
  /** Endpoint of an http server; may hold a ${VAR} reference. */
  url?: string;
  /** Executable of a stdio server. */
  command?: string;
  args?: string[];
  /** HTTP headers of an http server; a value may reference ${VAR}. */
  headers?: Record<string, string>;
  /** Environment of a stdio server; a value may reference ${VAR}. */
  env?: Record<string, string>;
}

export interface Room {
  id: string;
  slug: string;
  name: string;
}

export interface SeatTypeModuleRef {
  slug: string;
  version: string;
}

export interface SeatType {
  slug: string;
  name: string;
  description: string;
  /** From the latest version; null for a seat type with no version. */
  default_runtime: SeatRuntime | null;
  latest_version: string | null;
  module_refs: SeatTypeModuleRef[];
}

export interface Seat {
  id: string;
  room_id: string;
  seat_key: string;
  /** Seat type slug; the API also returns its opaque id. */
  seat_type: string;
  seat_type_id: string;
  pinned_version: string | null;
  runtime: string;
  model: string;
  permission_policy: SeatPermissionPolicy;
}

export interface SeatModuleVersion {
  slug: string;
  kind: SeatModuleKind;
  version: string;
  content: string;
  checksum: string;
}

// =============================================================================
// Overlays
// =============================================================================

export type SeatOverlayScope = 'seat' | 'room' | 'company';

export type SeatOverlayOpKind = 'add' | 'remove' | 'override' | 'pin';

export interface SeatOverlayOp {
  kind: SeatOverlayOpKind;
  slug: string;
  version: string;
  content: string;
}

export interface SeatOverlay {
  id?: string;
  scope: SeatOverlayScope;
  room_id?: string;
  seat_id?: string;
  ops: SeatOverlayOp[];
}

/** The three overlays that apply to one seat, in resolution order. */
export interface SeatOverlays {
  company: SeatOverlay;
  room: SeatOverlay;
  seat: SeatOverlay;
}

/**
 * One module of the effective seat after overlays are applied. `changes`
 * records the overlay op kinds that touched the module; `contentOverride` is
 * set when an override op replaces the module content.
 */
export interface EffectiveSeatModule {
  slug: string;
  version: string;
  overridden: boolean;
  removed: boolean;
  changes: SeatModuleChange[];
  contentOverride?: string;
}

export interface SeatModuleChange {
  scope: SeatOverlayScope;
  kind: SeatOverlayOpKind;
}

// =============================================================================
// Links
// =============================================================================

/** The five edge kinds OpenRig accepts. */
export type SeatLinkKind =
  | 'delegates_to'
  | 'spawned_by'
  | 'can_observe'
  | 'collaborates_with'
  | 'escalates_to';

export interface SeatLinkKindOption {
  kind: SeatLinkKind;
  /** Short plain-English label shown in the Links tab. */
  label: string;
  /** One-line hint for the kind. */
  hint: string;
}

/** Single source of truth for the link kinds offered in the UI. */
export const SEAT_LINK_KINDS: SeatLinkKindOption[] = [
  { kind: 'delegates_to', label: 'Gives work to', hint: 'Launches first.' },
  { kind: 'spawned_by', label: 'Was created by', hint: 'Parent launches first.' },
  {
    kind: 'can_observe',
    label: 'Can observe',
    hint: 'Can read the output of; does not allow sending.',
  },
  { kind: 'collaborates_with', label: 'Collaborates with', hint: 'Peer.' },
  { kind: 'escalates_to', label: 'Escalates to', hint: 'Escalates problems up to.' },
];

export interface SeatLink {
  id: string;
  from_seat_id: string;
  to_seat_id: string;
  kind: SeatLinkKind;
  allow: boolean;
}

// =============================================================================
// Preview (resolved snapshot)
// =============================================================================

export interface ResolvedSeatFile {
  path: string;
  content: string;
}

export interface ResolvedSeat {
  room: string;
  seat: string;
  hash: string;
  runtime: string;
  files: ResolvedSeatFile[];
  policy: Record<string, unknown>;
}

// =============================================================================
// Bridge machines (live status reported by scripts/openrig_bridge.py)
// =============================================================================

export type SeatRunState = 'running' | 'idle' | 'blocked' | 'stopped' | 'unknown';

/** Running hash against the seat's latest resolved snapshot, computed by the server. */
export type SeatSync = 'in_sync' | 'drift' | 'unknown';

export interface MachineSeatStatus {
  room: string;
  seat: string;
  state: SeatRunState;
  runtime: string;
  /** Hash the machine is running. */
  hash: string;
  /** Hash of the seat's latest resolved snapshot; empty when the seat is not in the cloud. */
  expected_hash: string;
  sync: SeatSync;
  detail: string;
  redacted: boolean;
  reported_at: string;
}

export interface MachineAgentStatus {
  agent: string;
  status: 'idle' | 'working' | 'blocked' | 'done' | 'unknown';
  pane_id: string;
}

export interface MachineStatus {
  machine_id: string;
  last_seen: string;
  online: boolean;
  seats: MachineSeatStatus[];
  agents: MachineAgentStatus[];
}

// =============================================================================
// Settings
// =============================================================================

export interface SeatSettings {
  follow_latest: boolean;
}

// =============================================================================
// Requests
// =============================================================================

export interface CreateRoomRequest {
  slug: string;
  name: string;
}

/**
 * New seats pin their seat type's latest version unless `follow_latest` is
 * true. Omitting both lets the company setting decide.
 */
export interface CreateSeatRequest {
  seat_key: string;
  seat_type: string;
  runtime: SeatRuntime;
  model: string;
  pinned_version?: string;
  follow_latest?: boolean;
}

export interface SeatLinkRequest {
  to_seat: string;
  kind: SeatLinkKind;
  allow: boolean;
}

/** An empty model means the runtime default. */
export interface OccupantUpdate {
  runtime: SeatRuntime;
  model: string;
}

/** Publishes one immutable module version; the slug and version are in the path. */
export interface PutModuleVersionRequest {
  kind: SeatModuleKind;
  content: string;
}

/** The server assigns the version (next patch of the latest); refs are `slug@x.y.z`. */
export interface CreateSeatTypeVersionRequest {
  module_refs: string[];
  default_runtime: SeatRuntime;
}

export interface PutSeatOverlayRequest {
  ops: SeatOverlayOp[];
}

/**
 * How the add-seat dialog decides the new seat's version policy.
 * - pin-latest: pin the current latest version (follow_latest: false)
 * - follow-latest: track the seat type's latest version (follow_latest: true)
 * - company-default: neither field, the company setting decides
 */
export type SeatPinChoice = 'pin-latest' | 'follow-latest' | 'company-default';

// =============================================================================
// Component props
// =============================================================================

export interface SeatModulesTabProps {
  seatType: SeatType | undefined;
}

export interface SeatLlmPanelProps {
  room: string;
  seat: Seat;
}

export interface SeatPermissionPolicyPanelProps {
  room: string;
  seat: Seat;
}

export interface SeatLinksTabProps {
  roomSeats: Seat[];
}

// =============================================================================
// API responses
// =============================================================================

export interface RoomsResponse {
  success: boolean;
  rooms: Room[];
}

export interface RoomResponse {
  success: boolean;
  room: Room;
}

export interface SeatTypesResponse {
  success: boolean;
  seat_types: SeatType[];
}

export interface ModuleVersionResponse {
  success: boolean;
  module: SeatModuleVersion;
}

export interface PublishedModuleVersion {
  slug: string;
  kind: SeatModuleKind;
  version: string;
  sha256: string;
}

/** Latest version of one module, without its content. */
export type ModuleSummary = PublishedModuleVersion;

export interface ModulesResponse {
  success: boolean;
  modules: ModuleSummary[];
}

export interface SeatTypeVersion {
  slug: string;
  version: string;
  default_runtime: SeatRuntime;
  module_refs: SeatTypeModuleRef[];
}

export interface SeatTypeVersionResponse {
  success: boolean;
  seat_type_version: SeatTypeVersion;
}

export interface PutModuleVersionResponse {
  success: boolean;
  module: PublishedModuleVersion;
}

export interface SeatsResponse {
  success: boolean;
  seats: Seat[];
}

export interface SeatResponse {
  success: boolean;
  seat: Seat;
}

export interface DeletedResponse {
  success: boolean;
}

export interface SeatOverlayResponse {
  success: boolean;
  overlay: SeatOverlay;
}

export interface SeatLinksResponse {
  success: boolean;
  links: SeatLink[];
}

export interface SeatLinkResponse {
  success: boolean;
  link: SeatLink;
}

export interface SeatSettingsResponse {
  success: boolean;
  settings: SeatSettings;
}

export interface ResolvedSeatResponse {
  success: boolean;
  resolved_seat: ResolvedSeat;
}

export interface MachinesResponse {
  success: boolean;
  machines: MachineStatus[];
}
