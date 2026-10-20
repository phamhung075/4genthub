-- 0007: the seat occupant record table.
--
-- 0001 is the FROZEN baseline and is skipped on any database whose catalogue already holds
-- tables, so a database that predates this table gets it only through a step like this one.
-- Every statement is idempotent, so a fresh database - which took the table from 0001 - is a no-op.

CREATE TABLE IF NOT EXISTS seat_occupant_changes (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	seat_id UUID NOT NULL REFERENCES seats (id) ON DELETE CASCADE,
	actor TEXT NOT NULL,
	at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	from_runtime TEXT NOT NULL,
	from_model TEXT NOT NULL,
	to_runtime TEXT NOT NULL,
	to_model TEXT NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_seat_occupant_changes_seat ON seat_occupant_changes (user_id, seat_id, at DESC);
