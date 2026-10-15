-- The seat_feedback layer `openrig` is now `client`: the closed layer set names the 4genteam client.
--
-- Idempotent: a database created from 0001 already carries the new CHECK and holds no `openrig` row,
-- so the UPDATE matches nothing and the constraint is replaced by an identical one.
ALTER TABLE seat_feedback DROP CONSTRAINT IF EXISTS ck_seat_feedback_layer;
UPDATE seat_feedback SET layer = 'client' WHERE layer = 'openrig';
ALTER TABLE seat_feedback ADD CONSTRAINT ck_seat_feedback_layer
	CHECK (layer IN ('runtime', 'client', 'cloud', 'seat-context', 'workspace', 'other'));
