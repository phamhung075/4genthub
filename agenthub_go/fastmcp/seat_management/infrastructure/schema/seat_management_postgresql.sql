-- ================================================================================
-- SEAT MANAGEMENT DATABASE SCHEMA - POSTGRESQL
-- ================================================================================
-- Company-workplace seat system. PostgreSQL DDL only.
--
-- Idempotent: every statement uses CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT
-- EXISTS / CREATE EXTENSION IF NOT EXISTS, so the file can be applied repeatedly.
--
-- Multi-tenancy: every table carries a `user_id` TEXT tenant column, matching the
-- project convention for user-scoped rows (see agents.user_id in init_schema_postgresql.sql).
-- There are no foreign keys to a users table.
--
-- NO foreign key CASCADE anywhere: the project deliberately keeps cascading deletes in
-- the application layer (DDD), so every reference below is a plain REFERENCES.
--
-- IMMUTABLE TABLES: module_versions, seat_type_versions and resolved_seats are append-only.
-- The application never issues an UPDATE against them (there is no UPDATE path).
--
-- user_settings_follow_latest is intentionally NOT a table here: "follow latest" will be a
-- column added to an existing settings table later, not a new table.
-- ================================================================================

-- IDS COME FROM THE APPLICATION, NOT FROM A SERVER DEFAULT.
--
-- Every id column below is declared WITHOUT a DEFAULT, because the runtime DDL that createAll
-- executes (infrastructure/database/seat_tables.go) declares none either and the Go layer
-- generates the value (ColumnDef.Default = taskdb.DefaultUUIDv4 -> tmvo.NewUUIDv4(),
-- base_orm_repository.go). THE TWO SOURCES MUST SAY THE SAME THING: this file used to carry
-- `DEFAULT uuid_generate_v4()` while the runtime declared none, which made a database created
-- from the FILE behave differently from one the RUNTIME path created — an insert that omitted
-- the id worked on the first and failed with a not-null violation on the second (measured
-- 2026-10-06, both directions: the D5 sharing test and the feedback boot test).
--
-- The uuid-ossp extension is deliberately NOT created here: nothing in this schema needs it any
-- more, and createAll never created it, so a runtime-built database never had it — which is the
-- other half of why a server default could not be honoured on a fresh database.
-- TestSeatDDLParity compares the columns, the REFERENCES, the CHECKs AND the DEFAULTs of both
-- sources, so this divergence cannot come back silently.

-- ================================================================================
-- CREATE TABLES
-- ================================================================================

-- Table: modules
-- A named, tenant-scoped unit of seat content.
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_modules_user_slug UNIQUE (user_id, slug),
    CONSTRAINT ck_modules_kind CHECK (kind IN ('instruction', 'document', 'skill', 'tool', 'mcp', 'memory', 'policy'))
);

CREATE INDEX IF NOT EXISTS ix_modules_user_id ON modules (user_id);

-- Table: module_versions
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- checksum is the lowercase sha256 hex digest of content.
CREATE TABLE IF NOT EXISTS module_versions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    module_id UUID NOT NULL REFERENCES modules (id),
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_module_versions_module_version UNIQUE (module_id, version)
);

CREATE INDEX IF NOT EXISTS ix_module_versions_user_id ON module_versions (user_id);
CREATE INDEX IF NOT EXISTS ix_module_versions_module_id ON module_versions (module_id);

-- Table: seat_types
-- A tenant-scoped template for a seat; its default runtime and module set live in the versions.
CREATE TABLE IF NOT EXISTS seat_types (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_types_user_slug UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_seat_types_user_id ON seat_types (user_id);

-- Table: seat_type_versions
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- default_runtime is the runtime of a seat that sets none. module_refs is a JSON array of
-- {"slug": ..., "version": ...} objects.
CREATE TABLE IF NOT EXISTS seat_type_versions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    seat_type_id UUID NOT NULL REFERENCES seat_types (id),
    version TEXT NOT NULL,
    default_runtime TEXT NOT NULL,
    module_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_type_versions_seat_type_version UNIQUE (seat_type_id, version)
);

CREATE INDEX IF NOT EXISTS ix_seat_type_versions_user_id ON seat_type_versions (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_type_versions_seat_type_id ON seat_type_versions (seat_type_id);

-- ================================================================================
-- TEAMS (NEXT_GEN D5) — the account boundary for sharing
-- ================================================================================
-- A team is the tenant whose data its members share. The user who creates the team
-- (teams.user_id) is its one owner, and team_members.role is 'owner' for that row and
-- 'viewer' for every other member. team_members.team_id dates from slice 1; the WIRING
-- column is rooms.team_id below, which shares one room with one team. No foreign key CASCADE.
--
-- THIS SECTION COMES BEFORE rooms ON PURPOSE: rooms.team_id references teams (id), and this
-- file is applied top-down, so the referenced table must exist first. seat_tables.go
-- registers these two tables first for the same reason, and the two orders must agree.

-- Table: teams
-- A team. user_id is the owning user and the tenant column, matching every other table.
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_teams_user_slug UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_teams_user_id ON teams (user_id);

-- Table: team_members
-- One user's membership in one team, with the role that user holds.
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY,
    team_id UUID NOT NULL REFERENCES teams (id),
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id),
    CONSTRAINT ck_team_members_role CHECK (role IN ('owner', 'viewer'))
);

CREATE INDEX IF NOT EXISTS ix_team_members_team_id ON team_members (team_id);
CREATE INDEX IF NOT EXISTS ix_team_members_user_id ON team_members (user_id);

-- At most one owner per team. The service also refuses a second owner, but the schema holds
-- the invariant: two owner rows would let both be demoted and leave the team ownerless.
CREATE UNIQUE INDEX IF NOT EXISTS uq_team_members_one_owner ON team_members (team_id) WHERE role = 'owner';

-- Table: rooms
-- A tenant-scoped grouping of seats.
-- rooms.name is unbounded TEXT; its length limit is repositories.MaxRoomNameLength (domain/repositories/repositories.go).
-- team_id NULL means the room is private to its owner. A non-NULL team_id shares the room,
-- read-only, with that team's members (the NEXT_GEN D5 wiring): every read of the room and of
-- what hangs off it admits a member of that team, and every write still matches user_id, so a
-- viewer cannot mutate. Plain REFERENCES, no CASCADE: the application clears the column.
CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    team_id UUID REFERENCES teams (id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_rooms_user_slug UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_rooms_user_id ON rooms (user_id);
CREATE INDEX IF NOT EXISTS ix_rooms_team_id ON rooms (team_id);

-- Table: seats
-- A seat inside a room. seat_key is the OpenRig member id.
-- pinned_version NULL means the seat follows the seat type's latest version.
-- permission_policy is the OpenRig permission_policy name rendered on the member.
CREATE TABLE IF NOT EXISTS seats (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    room_id UUID NOT NULL REFERENCES rooms (id),
    seat_key TEXT NOT NULL,
    seat_type_id UUID NOT NULL REFERENCES seat_types (id),
    pinned_version TEXT,
    runtime TEXT NOT NULL,
    model TEXT NOT NULL,
    permission_policy TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seats_room_seat_key UNIQUE (room_id, seat_key),
    CONSTRAINT ck_seats_permission_policy CHECK (permission_policy IN ('locked', 'standard', 'open', 'yolo', 'none'))
);

CREATE INDEX IF NOT EXISTS ix_seats_user_id ON seats (user_id);
CREATE INDEX IF NOT EXISTS ix_seats_room_id ON seats (room_id);
CREATE INDEX IF NOT EXISTS ix_seats_seat_type_id ON seats (seat_type_id);

-- Table: overlays
-- An ordered JSON array of {kind, slug, version, content} ops applied to one scope target.
-- scope=company has no room_id/seat_id, scope=room has room_id only, scope=seat has seat_id only.
CREATE TABLE IF NOT EXISTS overlays (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    room_id UUID REFERENCES rooms (id),
    seat_id UUID REFERENCES seats (id),
    ops JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_overlays_scope CHECK (scope IN ('company', 'room', 'seat')),
    CONSTRAINT ck_overlays_scope_target CHECK (
        (scope = 'company' AND room_id IS NULL AND seat_id IS NULL)
        OR (scope = 'room' AND room_id IS NOT NULL AND seat_id IS NULL)
        OR (scope = 'seat' AND seat_id IS NOT NULL AND room_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_overlays_user_id ON overlays (user_id);
CREATE INDEX IF NOT EXISTS ix_overlays_room_id ON overlays (room_id);
CREATE INDEX IF NOT EXISTS ix_overlays_seat_id ON overlays (seat_id);
-- One overlay per scope target: the zero UUID stands in for the NULL target column.
CREATE UNIQUE INDEX IF NOT EXISTS uq_overlays_target ON overlays (user_id, scope, COALESCE(room_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(seat_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- Table: seat_links
-- A directed communication edge between two seats.
CREATE TABLE IF NOT EXISTS seat_links (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    from_seat_id UUID NOT NULL REFERENCES seats (id),
    to_seat_id UUID NOT NULL REFERENCES seats (id),
    kind TEXT NOT NULL,
    allow BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_links_from_to_kind UNIQUE (from_seat_id, to_seat_id, kind),
    CONSTRAINT ck_seat_links_kind CHECK (kind IN ('delegates_to', 'spawned_by', 'can_observe', 'collaborates_with', 'escalates_to')),
    CONSTRAINT ck_seat_links_distinct CHECK (from_seat_id <> to_seat_id)
);

CREATE INDEX IF NOT EXISTS ix_seat_links_user_id ON seat_links (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_from_seat_id ON seat_links (from_seat_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_to_seat_id ON seat_links (to_seat_id);

-- Table: resolved_seats
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- files is a JSON array of {path, content}; policy is a JSON object.
CREATE TABLE IF NOT EXISTS resolved_seats (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    seat_id UUID NOT NULL REFERENCES seats (id),
    hash TEXT NOT NULL,
    runtime TEXT NOT NULL,
    files JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_resolved_seats_seat_hash UNIQUE (seat_id, hash)
);

CREATE INDEX IF NOT EXISTS ix_resolved_seats_user_id ON resolved_seats (user_id);
CREATE INDEX IF NOT EXISTS ix_resolved_seats_seat_id ON resolved_seats (seat_id);

-- Table: seat_settings
-- One settings row per user, keyed by user_id. follow_latest is the company default applied
-- to a new seat when the create request omits follow_latest and pinned_version.
CREATE TABLE IF NOT EXISTS seat_settings (
    user_id TEXT PRIMARY KEY,
    follow_latest BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Table: seat_feedback
-- The seat friction channel: what a seat (or its operator, or a bridge reporting for its seats)
-- hit, and in which layer of the platform. layer is a closed vocabulary with a CHECK rather than
-- a tag, because the read side GROUPS by it; its Go source of truth is
-- fastmcp/seat_management/domain/feedback, and TestSeatFeedbackLayerCheckMatchesDomain holds the
-- two together. room and seat are slugs, not references: friction stays readable after the seat
-- it is about is gone, which is the point of the channel. machine_id is empty when a user token
-- submitted the row and names the bridge when a machine token did. The row is append-only in use:
-- nothing updates or deletes it.
CREATE TABLE IF NOT EXISTS seat_feedback (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    room TEXT NOT NULL,
    seat TEXT NOT NULL,
    session TEXT NOT NULL DEFAULT '',
    layer TEXT NOT NULL,
    text TEXT NOT NULL,
    machine_id TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_seat_feedback_layer CHECK (layer IN ('runtime', 'openrig', 'cloud', 'seat-context', 'workspace', 'other'))
);

CREATE INDEX IF NOT EXISTS ix_seat_feedback_user_id ON seat_feedback (user_id);

-- Table: seat_messages
-- Text a window addressed to a seat, held until the client that holds that seat's terminal pulls it.
-- SEAT-OWNED AND KEYED BY THE REPORTED NAMES, like seat_feedback, and for a stronger reason: no seat
-- table carries a session column, so the server cannot address a session from a seat at all, and the
-- point of this store is to hold a message while the seat is DOWN. It is also the FIRST
-- SERVER-AUTHORED ROW A CLIENT CONSUMES on this axis — every other store here (seat_status,
-- seat_feedback, the session stream) is client-authored.
-- delivered_at and machine_id ARE the ack: delivery is at-least-once, so a row with delivered_at NULL
-- is pending and comes back on the next pull, while an acked one never does, and machine_id records
-- which machine actually took it. There is NO TTL: a message for a seat that never comes back stays
-- readable, and any bound would be explicit policy rather than a sweep (missed_notifications is the
-- precedent). Room and seat are names rather than references, so the deletion path removes these rows
-- itself — this schema has no CASCADE by design.
CREATE TABLE IF NOT EXISTS seat_messages (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    room TEXT NOT NULL,
    seat TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    machine_id TEXT NOT NULL DEFAULT ''
);

-- ONE index serves both jobs: the pull walks (user_id, room, seat) for pending rows in (created_at,
-- id) order, and the seat- and room-level deletes take a prefix of the same key.
CREATE INDEX IF NOT EXISTS ix_seat_messages_seat ON seat_messages (user_id, room, seat, created_at, id);

-- Table: machines
-- One row per (user, bridge machine). agents is the latest herdr agent snapshot, a JSON
-- array of {agent, status, pane_id}; last_seen is server time of the last status report.
CREATE TABLE IF NOT EXISTS machines (
    user_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    agents JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (user_id, machine_id)
);

-- Table: seat_status
-- The latest reported state of each seat on a machine. A report replaces the machine's
-- whole set; room and seat are reported names, not foreign keys.
CREATE TABLE IF NOT EXISTS seat_status (
    user_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    room TEXT NOT NULL,
    seat TEXT NOT NULL,
    state TEXT NOT NULL,
    runtime TEXT NOT NULL,
    running_hash TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    redacted BOOLEAN NOT NULL DEFAULT false,
    reported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (user_id, machine_id, room, seat)
);

-- Table: machine_edges
-- The topology a machine reported: one row per directed link of one room, replaced wholesale by
-- each report exactly like seat_status. room, from_seat and to_seat are reported names, not
-- foreign keys, so an edge is removed by the application layer when its room is deleted - the
-- no-CASCADE rule the rest of this schema follows. `from` and `to` are SQL keywords, hence the
-- from_seat/to_seat spellings; the wire names the two ends from and to.
CREATE TABLE IF NOT EXISTS machine_edges (
    user_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    room TEXT NOT NULL,
    from_seat TEXT NOT NULL,
    to_seat TEXT NOT NULL,
    kind TEXT NOT NULL,
    CONSTRAINT ck_machine_edges_kind CHECK (kind IN ('delegates_to', 'spawned_by', 'can_observe', 'collaborates_with', 'escalates_to')),
    CONSTRAINT ck_machine_edges_distinct CHECK (from_seat <> to_seat),
    PRIMARY KEY (user_id, machine_id, room, from_seat, to_seat, kind)
);

CREATE INDEX IF NOT EXISTS ix_machine_edges_user_room ON machine_edges (user_id, room);
