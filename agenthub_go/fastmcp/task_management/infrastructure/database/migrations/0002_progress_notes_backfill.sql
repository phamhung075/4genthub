-- THE CARRY: progress notes that live ONLY in the column reach the ledger.
--
-- NOT the step NEXT_GEN's O1c rules as "the carry step" (decision D1 3a): that one also DROPs
-- progress_history and progress_count, and it runs only under the owner's `0001` baseline mark. This
-- step is additive and only backfills; the columns stay, which is what keeps the union read correct
-- while the switch is half landed.
--
-- WHY THIS STEP EXISTS. O1c moves progress notes from tasks.progress_history (and the subtasks twin)
-- into the task_events ledger. Before that switch every note was written to the column alone; after it
-- a note is written to BOTH, which is why domain/entities/task.go's ProgressTextWith merges the two
-- sources by the identity the payload declares. The union is correct, but it was load-bearing: the
-- column held the notes written before the switch and the ledger held the ones written after it, so a
-- reader that had only the ledger - the ledger timeline the switch dialog shows - was missing every
-- pre-switch note. This step copies those notes into the ledger, so the ledger alone is complete and
-- the union is a merge rule rather than the only thing that can show an old note.
--
-- WHAT A CARRIED NOTE LOOKS LIKE. Exactly the payload application/services/task_event_recorder.go's
-- RecordProgress writes for a live note - content (the text WITH its numbered header, as the column
-- stores it), progress_number, timestamp - plus `carried_from`, the column key it was copied from.
-- ProgressTextWith reads the identity as content + progress_number, which is what makes a carried copy
-- of a note that is already present render ONCE rather than twice, and `carried_from` is the record
-- that this entry is a copy rather than a write.
--
-- WHY `human` AND NOT A NEW ACTOR KIND. The ledger's actor_kind vocabulary is closed
-- ('seat', 'client', 'gate', 'human') and a carried note was written by the user the row belongs to,
-- before any seat attributed writes, so attributing it to that user is the truthful value. Inventing a
-- 'carry' actor would widen a closed vocabulary to describe the migration rather than the note.
--
-- IDEMPOTENT BY GUARD, NOT ONLY BY THE LEDGER. The runner records this step and never re-runs it, and
-- the NOT EXISTS below additionally skips any note the ledger already holds under the same identity,
-- so a database that somehow holds part of the carry converges instead of duplicating it.
--
-- A MALFORMED ENTRY IS SKIPPED, NOT A FAILURE, AND THAT DIFFERS ON PURPOSE FROM THE STEP O1c RULES.
-- The ruled carry step also DROPs the two columns, so a note it cannot read is a note it would
-- destroy, and it must fail rather than lose it (`NEXT_GEN.md`'s O1c check: "a malformed entry -> step
-- fails, column intact"). This step destroys nothing - the columns stay - so an entry the ledger
-- cannot express is left exactly where it is, and the reader's union still shows it.
--
-- LOCKED AGAINST LIVE APPENDS. The runner holds its own advisory lock, but an append takes the
-- per-user lock in TaskEventRepository.AppendInTx, which is a different key: without this the MAX+1
-- numbering below could race a live append and either side could collide on the uniques. The first
-- statement takes each affected user's lock for the rest of this transaction, in the same key the
-- append path uses.

SELECT pg_advisory_xact_lock(hashtext(u.user_id::text))
FROM (
    SELECT DISTINCT user_id FROM tasks
    UNION
    SELECT DISTINCT user_id FROM subtasks
) AS u;

WITH notes AS (
    -- Every stored note, in both tables, with the shape the column writes: the key it is stored under
    -- (progress_N), the content as stored (numbered header included), the number, and the timestamp.
    --
    -- to_jsonb() rather than json_each or jsonb_each directly: a schema created by the DDL source
    -- gives this column jsonb and one created by the table definitions may give it json, and each
    -- _each function accepts only its own type. The type check keeps a column that holds a scalar or
    -- null - which neither function iterates - from failing the step.
    SELECT t.user_id,
           t.id                      AS task_id,
           NULL::uuid                AS subtask_id,
           e.key                     AS col_key,
           (e.value ->> 'content')   AS content,
           (e.value ->> 'progress_number')::double precision AS number,
           COALESCE(e.value ->> 'timestamp', '')             AS ts
    FROM tasks t
    CROSS JOIN LATERAL jsonb_each(to_jsonb(t.progress_history)) AS e(key, value)
    WHERE jsonb_typeof(to_jsonb(t.progress_history)) = 'object'
    UNION ALL
    SELECT s.user_id,
           s.task_id,
           s.id,
           e.key,
           (e.value ->> 'content'),
           (e.value ->> 'progress_number')::double precision,
           COALESCE(e.value ->> 'timestamp', '')
    FROM subtasks s
    CROSS JOIN LATERAL jsonb_each(to_jsonb(s.progress_history)) AS e(key, value)
    WHERE jsonb_typeof(to_jsonb(s.progress_history)) = 'object'
),
missing AS (
    SELECT n.*
    FROM notes n
    WHERE n.content IS NOT NULL
      AND n.number IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM task_events te
          WHERE te.user_id = n.user_id
            AND te.task_id = n.task_id
            AND te.kind = 'progress'
            AND (te.payload ->> 'progress_number')::double precision = n.number
            AND (te.payload ->> 'content') = n.content
      )
),
user_tip AS (
    SELECT user_id, COALESCE(MAX(user_seq), 0) AS base FROM task_events GROUP BY user_id
),
task_tip AS (
    SELECT user_id, task_id, COALESCE(MAX(seq), 0) AS base FROM task_events GROUP BY user_id, task_id
)
INSERT INTO task_events (id, user_id, task_id, subtask_id, seq, user_seq, kind, actor_kind, actor_id, payload)
SELECT gen_random_uuid(),
       m.user_id,
       m.task_id,
       m.subtask_id,
       COALESCE(tt.base, 0) + ROW_NUMBER() OVER (
           PARTITION BY m.user_id, m.task_id ORDER BY m.number, m.col_key),
       COALESCE(ut.base, 0) + ROW_NUMBER() OVER (
           PARTITION BY m.user_id ORDER BY m.task_id, m.number, m.col_key),
       'progress',
       'human',
       m.user_id,
       json_build_object(
           'content',         m.content,
           'progress_number', m.number,
           'timestamp',       m.ts,
           'carried_from',    m.col_key
       )
FROM missing m
LEFT JOIN user_tip ut ON ut.user_id = m.user_id
LEFT JOIN task_tip tt ON tt.user_id = m.user_id AND tt.task_id = m.task_id;
