-- ================================================================================
-- ROOM SAFEGUARD DATABASE SCHEMA - POSTGRESQL
-- ================================================================================
-- The server's store for the `safeguard` socket frame (ai_docs/core-architecture/agent-boundaries.md
-- 7.3): one row per safeguard per room per connector, holding the LATEST state the connector
-- reported. The frame is an upsert - no seq, no cursor and no ack - so the table has no history and
-- no id: the key IS the identity, and a re-sent row is the same row.
--
-- Idempotent: every statement uses CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS, so the
-- file can be applied repeatedly. The runtime path (createAll over
-- fastmcp/room_safeguard/infrastructure/database/room_safeguard_tables.go) creates the same table on a
-- fresh database, and TestRoomSafeguardSchemaAgreesWithTheORMRow compares the two sources and the row
-- struct's db tags, so the two cannot diverge silently.
--
-- user_id is on the table and every statement filters by it, like every other table here.
-- NO foreign key and NO CASCADE: connector_id is the connector's own name from the hello frame, not
-- a row of another table, and this project keeps cascades in the application layer.
--
-- last_beat_at is the frame's `at` - the child's own beat time - and NULL when the frame carried
-- none. It is never the server's receive time: a column that reports a beat the child did not make
-- would be a lie in the middle of the one table built to notice silence.
--
-- 7.2's started_at is deliberately absent: the frame carries no started_at, so the server has no
-- value for it.
-- ================================================================================

CREATE TABLE IF NOT EXISTS room_safeguards (
    user_id VARCHAR(64) NOT NULL,
    connector_id VARCHAR(64) NOT NULL,
    room VARCHAR(255) NOT NULL,
    safeguard VARCHAR(32) NOT NULL,
    state VARCHAR(20) NOT NULL,
    pid INTEGER,
    restarts INTEGER NOT NULL,
    age_s INTEGER NOT NULL,
    last_beat_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (user_id, connector_id, room, safeguard),
    -- The closed set of 7.6 and the room rule that belongs to each name's scope, stated to the
    -- database so no path can store a safeguard or a room the vocabulary does not name. ck_..._room is
    -- the scope rule the ingest states too: a room-scoped safeguard needs a room of 1..255, and the two
    -- machine-scoped ones (bridge, agent) need exactly none. room VARCHAR(255) already caps the upper
    -- bound; it is stated here so the constraint reads as the rule the code states. The ingest refuses
    -- a bad row first, with a frame error rather than a constraint violation.
    CONSTRAINT ck_room_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
    CONSTRAINT ck_room_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'messages', 'roomguard', 'budget', 'bridge', 'agent')),
    CONSTRAINT ck_room_safeguards_room CHECK (CASE WHEN safeguard IN ('bridge', 'agent') THEN room = '' ELSE length(room) BETWEEN 1 AND 255 END)
);

CREATE INDEX IF NOT EXISTS ix_room_safeguards_user_connector ON room_safeguards (user_id, connector_id);
