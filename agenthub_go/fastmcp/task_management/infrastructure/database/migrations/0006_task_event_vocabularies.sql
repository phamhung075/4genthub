-- 0006: task_events' two closed vocabularies, re-created from their ruled sets.
--
-- THIS IS 0005's SECOND HALF, and it is a separate step for the reason the former ensurer gave: the
-- columns in 0005 must land on ANY database, while recreating a CHECK validates every existing row -
-- a database whose rows carry the older vocabulary (user|system|agent) cannot satisfy these sets
-- without a data move, and with both halves in one transaction that database would get no repair at
-- all and fail on a constraint instead of the column it actually needed. On the real ledger it cannot
-- arise: nothing wrote task_events before P1's reader landed.
--
-- The deleted-kind assertion runs BEFORE the CHECK is dropped: dropping a value deletes no rows, so a
-- database still carrying one of the six removed kinds is REPORTED with its count - the thing an
-- operator has to migrate deliberately - rather than refused later by a constraint that names no
-- count.

DO $$ BEGIN
	IF EXISTS (SELECT 1 FROM task_events WHERE kind IN ('assigned', 'claimed', 'delivered', 'context_loaded', 'escalated', 'human_decision')) THEN
		RAISE EXCEPTION 'task_events: row(s) carry a deleted kind (assigned, claimed, delivered, context_loaded, escalated, human_decision); the narrowed CHECK cannot be added until they are migrated';
	END IF;
END $$;

ALTER TABLE task_events DROP CONSTRAINT IF EXISTS ck_task_event_kind;
ALTER TABLE task_events ADD CONSTRAINT ck_task_event_kind CHECK (kind IN ('progress', 'status_changed', 'evidence_submitted', 'gate_verdict', 'handover', 'context_updated'));
ALTER TABLE task_events DROP CONSTRAINT IF EXISTS ck_task_event_actor_kind;
ALTER TABLE task_events ADD CONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN ('seat', 'client', 'gate', 'human'));
