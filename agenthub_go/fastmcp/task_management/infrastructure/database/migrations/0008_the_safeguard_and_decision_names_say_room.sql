-- 0008: the safeguard table and the decision column say room.
--
-- The unit is the room (owner ruling 2026-10-20, DECISION-2026-10-20-rig-gone.md): the retired word
-- named the runtime's grouping, and every surface that stored it now stores the room. 0001 is the
-- frozen baseline and is skipped on any database that already holds tables, so an existing database
-- reaches the new names only through this step; a fresh database has them from 0001 and every
-- statement here is a guarded no-op on it.
--
-- WHY THE KEY AND THE INDEX ARE RENAMED WITH THE COLUMN. The primary key, the three CHECKs and the
-- connector index are named after the table and the column they cover - ck_<table>_<subject>, where
-- the suffix is the column the constraint reads. A rename that left them behind would leave
-- `ck_rig_safeguards_rig` guarding a column called `room`, which is the same defect this task deletes
-- in code. No statement here edits data: a rename carries every row.
--
-- A MISSING TABLE IS A NO-OP, NOT A FAILURE. The runner skips 0001 on a non-empty catalogue and the
-- registry creates its tables last, so a boot can reach this step before `room_safeguards` exists;
-- SQLSTATE 42P01 would take the whole boot down. It is guarded the way 0004 guards its first ALTER.

DO $$
BEGIN
    -- 1. The table and the column. A fresh database took both names from 0001 and skips both branches.
    IF to_regclass('rig_safeguards') IS NOT NULL THEN
        ALTER TABLE rig_safeguards RENAME TO room_safeguards;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'room_safeguards'
           AND column_name = 'rig'
    ) THEN
        ALTER TABLE room_safeguards RENAME COLUMN rig TO room;
    END IF;

    -- 2. The three CHECKs follow the table token and the column suffix.
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_rig_safeguards_state') THEN
        ALTER TABLE room_safeguards RENAME CONSTRAINT ck_rig_safeguards_state TO ck_room_safeguards_state;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_rig_safeguards_safeguard') THEN
        ALTER TABLE room_safeguards RENAME CONSTRAINT ck_rig_safeguards_safeguard TO ck_room_safeguards_safeguard;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_rig_safeguards_rig') THEN
        ALTER TABLE room_safeguards RENAME CONSTRAINT ck_rig_safeguards_rig TO ck_room_safeguards_room;
    END IF;

    -- 3. The primary key and its index are named after the table they hold.
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rig_safeguards_pkey') THEN
        ALTER TABLE room_safeguards RENAME CONSTRAINT rig_safeguards_pkey TO room_safeguards_pkey;
    END IF;
    IF to_regclass('ix_rig_safeguards_user_connector') IS NOT NULL THEN
        ALTER INDEX ix_rig_safeguards_user_connector RENAME TO ix_room_safeguards_user_connector;
    END IF;

    -- 4. room_decisions carries the room's name in a column of its own.
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'room_decisions'
           AND column_name = 'rig_name'
    ) THEN
        ALTER TABLE room_decisions RENAME COLUMN rig_name TO room_name;
    END IF;
END $$;
