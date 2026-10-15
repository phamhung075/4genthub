-- The safeguard vocabulary moves to the six names the client reports (7.2), and the rig rule follows
-- each name's scope: rig-scoped (compact, watchdog, messages, roomguard) need a rig of 1..255, the
-- two machine-scoped ones (bridge, agent) need EXACTLY none.
--
-- WHY THE STORED ROWS MOVE TOO. `rigd` is DELETED, not aliased: no client sends the name since
-- `bc725e6` (2026-10-15) renamed the machine-level supervisor to `agent`, and the name CHECK added
-- below refuses it. A stored `rigd` row would therefore be unreachable - nothing updates it, and the
-- constraint that follows this statement would reject it on any write - so the vocabulary in the table
-- has to follow the vocabulary on the wire: the row IS the agent row the client now publishes, with
-- the empty rig its scope demands.
--
-- THE ORDER IS THE FIRST FOUR STATEMENTS, and it is checked rather than reasoned: the constraints this
-- step replaces come off BEFORE the writes they would refuse - the name CHECK admits only
-- ('compact', 'watchdog', 'bridge', 'rigd') and rejects 'agent' on the UPDATE. The step is one
-- transaction (the runner holds each step's SQL and its ledger row together), so no other connection
-- ever reads the table without its constraints.
--
-- A MISSING TABLE IS A NO-OP, NOT A FAILURE, and it is the ordinary case on a fresh boot rather than
-- an exotic one. The engine creates its tables from the TableDef registry LAST (createAll, and the
-- init SQL before it), while the runner skips `0001_baseline` whenever the catalogue is not empty - so
-- a boot that reaches this step before the registry has created `rig_safeguards` would hit SQLSTATE
-- 42P01 on the first ALTER and take the WHOLE BOOT down, migrating nothing: measured, that is exactly
-- `TestDatabaseInitializerCreateDefaultProject`'s second boot failing on this step. There is nothing to
-- move in that database: the table is created from the TableDef and the schema file, and both state the
-- two ruled constraints below, so the step's subject does not exist yet and it must not invent it.

DO $$
BEGIN
    IF to_regclass('rig_safeguards') IS NULL THEN
        RETURN;
    END IF;

    -- 1. The constraints this step replaces come off first: the rename below writes a name the old one
    --    refuses, and the rig rule is new. Both are re-added from the ruled sets at the end.
    ALTER TABLE rig_safeguards DROP CONSTRAINT IF EXISTS ck_rig_safeguards_safeguard;
    ALTER TABLE rig_safeguards DROP CONSTRAINT IF EXISTS ck_rig_safeguards_rig;

    -- 2. The retired name becomes the name the client reports, with the empty rig its scope demands.
    UPDATE rig_safeguards SET safeguard = 'agent', rig = '' WHERE safeguard = 'rigd';

    -- 3. Rows no scope rule can accept are DROPPED, not merged. Two shapes can exist under the old
    --    constraint, because it stated no rig rule at all: a machine-scoped name carrying a rig (the old
    --    validate() demanded a rig for EVERY name, so a legacy `bridge` row has one) and a rig-scoped name
    --    with an empty rig (which only a writer that bypassed validate() could have stored). Neither is
    --    carried forward: the client republishes all six of its rows after every ready (7.2), so the next
    --    connect restores the row in its ruled shape, while a merge would invent a state no reporter sent.
    --    The table is dev data, which is what makes dropping it the cheap half of the trade.
    DELETE FROM rig_safeguards WHERE safeguard IN ('bridge', 'agent') AND rig <> '';
    DELETE FROM rig_safeguards
     WHERE safeguard IN ('compact', 'watchdog', 'messages', 'roomguard')
       AND (rig = '' OR length(rig) > 255);

    -- 4. The ruled constraints, the same two the schema file and the runtime TableDef state.
    ALTER TABLE rig_safeguards ADD CONSTRAINT ck_rig_safeguards_safeguard
        CHECK (safeguard IN ('compact', 'watchdog', 'messages', 'roomguard', 'bridge', 'agent'));

    -- `rig` is VARCHAR(255) already, so the upper bound is carried twice on purpose: the constraint reads
    -- as the rule validate() states to the connector, which is what the state and name CHECKs beside it do.
    ALTER TABLE rig_safeguards ADD CONSTRAINT ck_rig_safeguards_rig
        CHECK (CASE WHEN safeguard IN ('bridge', 'agent') THEN rig = ''
                    ELSE length(rig) BETWEEN 1 AND 255 END);
END $$;
