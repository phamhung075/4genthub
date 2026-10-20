-- 0009: the safeguard vocabulary admits `budget`, the seventh name and the fifth room-scoped one.
--
-- The client publishes seven rows after every `ready` (pin 6c25e316,
-- `internal/clientservices/services.go:45,114-116,166`): compact, watchdog, messages, roomguard,
-- budget, bridge, agent. The sixth-value CHECK this step replaces refused the `budget` row, so one
-- `bad_safeguard` was answered per ready and no budget row ever reached the table. `budget` is
-- ROOM-SCOPED (`services.go:119-122`, table `:166`), which is why the scope CHECK below is untouched:
-- it is not one of the machine-scoped pair, so it needs a room like the other four.
--
-- WHY THIS IS A NEW STEP AND NOT AN EDIT TO 0004 OR 0008. The runner applies a step ONCE, by its
-- file's base name, and records that name in `applied_migrations`; 0004 and 0008 are on `origin/main`
-- and have already run on every database whose CHECK still holds six values, so editing either one
-- is a no-op there. 0008 also carries no value list - it renames the table, the column and the
-- constraints, and the six values survive from 0004/0001.
--
-- NO DATA MOVE. Widening a CHECK refuses no stored row, so unlike 0004 nothing is renamed or deleted
-- and no pre-check over existing rows is needed.
--
-- A MISSING TABLE IS A NO-OP, NOT A FAILURE, the way 0004 and 0008 guard: the runner skips 0001 on a
-- non-empty catalogue and the registry creates its tables last, so a boot can reach this step before
-- `room_safeguards` exists. SQLSTATE 42P01 there would take the whole boot down.

DO $$
BEGIN
    IF to_regclass('room_safeguards') IS NULL THEN
        RETURN;
    END IF;

    ALTER TABLE room_safeguards DROP CONSTRAINT IF EXISTS ck_room_safeguards_safeguard;
    ALTER TABLE room_safeguards ADD CONSTRAINT ck_room_safeguards_safeguard
        CHECK (safeguard IN ('compact', 'watchdog', 'messages', 'roomguard', 'budget', 'bridge', 'agent'));
END $$;
