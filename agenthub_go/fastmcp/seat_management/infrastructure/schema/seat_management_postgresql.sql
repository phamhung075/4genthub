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

-- uuid_generate_v4() for the UUID primary key defaults, matching the existing schema.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================================
-- CREATE TABLES
-- ================================================================================

-- Table: modules
-- A named, tenant-scoped unit of seat content.
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_modules_user_slug UNIQUE (user_id, slug),
    CONSTRAINT ck_modules_kind CHECK (kind IN ('instruction', 'document', 'skill', 'tool', 'memory'))
);

CREATE INDEX IF NOT EXISTS ix_modules_user_id ON modules (user_id);

-- Table: module_versions
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- checksum is the lowercase sha256 hex digest of content.
CREATE TABLE IF NOT EXISTS module_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
-- A tenant-scoped template for a seat (default runtime plus a pinned module set).
CREATE TABLE IF NOT EXISTS seat_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    default_runtime TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_types_user_slug UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_seat_types_user_id ON seat_types (user_id);

-- Table: seat_type_versions
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- module_refs is a JSON array of {"slug": ..., "version": ...} objects.
CREATE TABLE IF NOT EXISTS seat_type_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    seat_type_id UUID NOT NULL REFERENCES seat_types (id),
    version TEXT NOT NULL,
    module_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_type_versions_seat_type_version UNIQUE (seat_type_id, version)
);

CREATE INDEX IF NOT EXISTS ix_seat_type_versions_user_id ON seat_type_versions (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_type_versions_seat_type_id ON seat_type_versions (seat_type_id);

-- Table: rooms
-- A tenant-scoped grouping of seats.
CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_rooms_user_slug UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_rooms_user_id ON rooms (user_id);

-- Table: seats
-- A seat inside a room. seat_key is the OpenRig member id.
-- pinned_version NULL means the seat follows the seat type's latest version.
CREATE TABLE IF NOT EXISTS seats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    room_id UUID NOT NULL REFERENCES rooms (id),
    seat_key TEXT NOT NULL,
    seat_type_id UUID NOT NULL REFERENCES seat_types (id),
    pinned_version TEXT,
    runtime TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seats_room_seat_key UNIQUE (room_id, seat_key),
    CONSTRAINT ck_seats_status CHECK (status IN ('active', 'removed'))
);

CREATE INDEX IF NOT EXISTS ix_seats_user_id ON seats (user_id);
CREATE INDEX IF NOT EXISTS ix_seats_room_id ON seats (room_id);
CREATE INDEX IF NOT EXISTS ix_seats_seat_type_id ON seats (seat_type_id);

-- Table: overlays
-- An ordered JSON array of {kind, slug, version, content} ops applied to one scope target.
-- scope=company has no room_id/seat_id, scope=room has room_id only, scope=seat has seat_id only.
CREATE TABLE IF NOT EXISTS overlays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    from_seat_id UUID NOT NULL REFERENCES seats (id),
    to_seat_id UUID NOT NULL REFERENCES seats (id),
    kind TEXT NOT NULL,
    allow BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_seat_links_from_to_kind UNIQUE (from_seat_id, to_seat_id, kind),
    CONSTRAINT ck_seat_links_kind CHECK (kind IN ('delegates_to', 'escalates_to', 'reports_to', 'consults', 'notifies')),
    CONSTRAINT ck_seat_links_distinct CHECK (from_seat_id <> to_seat_id)
);

CREATE INDEX IF NOT EXISTS ix_seat_links_user_id ON seat_links (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_from_seat_id ON seat_links (from_seat_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_to_seat_id ON seat_links (to_seat_id);

-- Table: resolved_seats
-- Immutable: append-only. The application never issues an UPDATE against this table.
-- files is a JSON array of {path, content}; policy is a JSON object.
CREATE TABLE IF NOT EXISTS resolved_seats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
