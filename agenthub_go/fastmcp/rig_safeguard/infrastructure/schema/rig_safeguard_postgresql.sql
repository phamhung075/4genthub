-- ================================================================================
-- RIG SAFEGUARD DATABASE SCHEMA - POSTGRESQL
-- ================================================================================
-- The server's store for the `safeguard` socket frame (ai_docs/core-architecture/rigd-boundaries.md
-- 7.3): one row per safeguard per rig per connector, holding the LATEST state the connector
-- reported. The frame is an upsert - no seq, no cursor and no ack - so the table has no history and
-- no id: the key IS the identity, and a re-sent row is the same row.
--
-- Idempotent: every statement uses CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS, so the
-- file can be applied repeatedly. The runtime path (createAll over
-- fastmcp/rig_safeguard/infrastructure/database/rig_safeguard_tables.go) creates the same table on a
-- fresh database, and TestRigSafeguardSchemaAgreesWithTheORMRow compares the two sources and the row
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

CREATE TABLE IF NOT EXISTS rig_safeguards (
    user_id VARCHAR(64) NOT NULL,
    connector_id VARCHAR(64) NOT NULL,
    rig VARCHAR(255) NOT NULL,
    safeguard VARCHAR(32) NOT NULL,
    state VARCHAR(20) NOT NULL,
    pid INTEGER,
    restarts INTEGER NOT NULL,
    age_s INTEGER NOT NULL,
    last_beat_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (user_id, connector_id, rig, safeguard),
    -- The two closed sets of 7.6, stated to the database so no path can store a state or a safeguard
    -- the vocabulary does not name. The ingest refuses them first, with a frame error rather than a
    -- constraint violation.
    CONSTRAINT ck_rig_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
    CONSTRAINT ck_rig_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'bridge', 'rigd'))
);

CREATE INDEX IF NOT EXISTS ix_rig_safeguards_user_connector ON rig_safeguards (user_id, connector_id);
