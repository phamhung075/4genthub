-- 0005: the columns the boot used to patch in, as a migration step.
--
-- WHAT THIS REPLACES. Until now a boot ran, in order: createAll (the TableDef registry), then
-- EnsureAIColumnsExist, then five registered "column ensurers" (session_stream, task_events,
-- completion_attribution, acceptance_scope, seat columns), and only then the migrations. That is
-- four schema creators. The ruling for this row (seat-tier decision 2026-10-17 22:45Z, option
-- "migrations") leaves ONE: the embedded steps, applied by Runner.Apply.
--
-- WHY THE COLUMNS ARE STILL NEEDED HERE. 0001 is the FROZEN baseline of the schema and is skipped
-- on any database whose catalogue already holds tables, so those columns reach a database that
-- predates them only through a step like this one. Every statement is idempotent (ADD COLUMN IF NOT
-- EXISTS / DROP IF EXISTS + ADD), so a fresh database - which took them from 0001 - is a no-op.
--
-- The definitions are the former ensurers' own statements, kept verbatim where they were:
--   tasks/subtasks acceptance_criteria, scope, completed_by   (acceptance_scope_ensurer.go,
--                                                             completion_attribution_ensurer.go)
--   tasks/subtasks ai_*                                       (ensure_ai_columns.go)
--   agent_sessions room_slug, seat_key, check, client_cursor, seat_state (session_columns.go)
--   task_events user_seq (backfilled), client_event_id, uniques (task_event_ensurer.go, part 1)
--   rooms/room_decisions                                      (ensure_seat_columns.go)
-- The task_events VOCABULARIES are 0006, because the former ensurer kept them in their own
-- transaction deliberately: recreating a CHECK validates every existing row, and a database whose
-- rows carry the old vocabulary must still get its columns.

-- tasks and subtasks: acceptance criteria and scope (JSON string arrays).
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS acceptance_criteria JSON NOT NULL DEFAULT '[]';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scope JSON NOT NULL DEFAULT '[]';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS acceptance_criteria JSON NOT NULL DEFAULT '[]';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS scope JSON NOT NULL DEFAULT '[]';

-- tasks: the seat whose completion line the row holds. '' means "no recorded author".
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_by VARCHAR NOT NULL DEFAULT '';

-- tasks and subtasks: the ai_* columns.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_work_context JSON DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_execution_history JSON DEFAULT '[]';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_model_preferences JSON DEFAULT '{}';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_work_context JSON DEFAULT '{}';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_execution_history JSON DEFAULT '[]';
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP DEFAULT NULL;
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS ai_model_preferences JSON DEFAULT '{}';

-- agent_sessions: the seat identity the connector reports, both-or-neither, plus its cursor and state.
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS room_slug VARCHAR(255);
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS seat_key VARCHAR(255);
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS client_cursor VARCHAR(512);
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS seat_state VARCHAR(20);
ALTER TABLE agent_sessions DROP CONSTRAINT IF EXISTS ck_agent_sessions_seat_pair;
ALTER TABLE agent_sessions ADD CONSTRAINT ck_agent_sessions_seat_pair CHECK ((room_slug IS NULL) = (seat_key IS NULL));

-- rooms: the D5 sharing column and its index; room_decisions: the answer leg's delivery marker.
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams (id);
CREATE INDEX IF NOT EXISTS ix_rooms_team_id ON rooms (team_id);
ALTER TABLE room_decisions ADD COLUMN IF NOT EXISTS acked_at TIMESTAMP WITH TIME ZONE;
-- The decisions column was renamed to room_name; this statement names it, so it carries the new
-- column. On a fresh database 0001 has already created the index under this name and the IF NOT
-- EXISTS is the no-op; on a database that applied this step the step is skipped, so no run reads
-- the old spelling. Only a database that stopped between 0004 and 0008 could miss the column, and
-- that state does not survive a boot.
CREATE INDEX IF NOT EXISTS ix_room_decisions_user_room_state_acked ON room_decisions (user_id, room_name, state, acked_at);
-- The superseded S1 idempotency key: a daemon's decisionId was globally unique, so a second tenant's
-- ask for the same local row raised 23505. Nothing declares it any more; the ruled replacement is the
-- tenant-scoped episode tuple.
ALTER TABLE room_decisions DROP CONSTRAINT IF EXISTS uq_room_decisions_idempotency_key;

-- task_events: the per-user sequence and the outbox key, and the numbering is per user, in
-- (created_at, id) order, ABOVE that user's current maximum - never restarting at 1 over rows that
-- already carry a value, because a collision would fail the unique this step is about to create.
ALTER TABLE task_events ADD COLUMN IF NOT EXISTS user_seq BIGINT;
ALTER TABLE task_events ADD COLUMN IF NOT EXISTS client_event_id UUID;
UPDATE task_events e SET user_seq = numbered.rn FROM (
	SELECT t.id,
	       COALESCE((SELECT MAX(m.user_seq) FROM task_events m WHERE m.user_id = t.user_id), 0)
	       + ROW_NUMBER() OVER (PARTITION BY t.user_id ORDER BY t.created_at, t.id) AS rn
	FROM task_events t WHERE t.user_seq IS NULL
) numbered WHERE e.id = numbered.id;
ALTER TABLE task_events ALTER COLUMN user_seq SET NOT NULL;
DO $$ BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_task_event_user_seq') THEN
		ALTER TABLE task_events ADD CONSTRAINT uq_task_event_user_seq UNIQUE (user_id, user_seq);
	END IF;
END $$;
DO $$ BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_task_event_client_event') THEN
		ALTER TABLE task_events ADD CONSTRAINT uq_task_event_client_event UNIQUE (user_id, client_event_id);
	END IF;
END $$;
