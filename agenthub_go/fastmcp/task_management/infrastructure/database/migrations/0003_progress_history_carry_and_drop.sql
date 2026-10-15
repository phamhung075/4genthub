-- THE CARRY STEP O1c RULES (decision D1 3a): the column's notes reach the ledger, the ledger is
-- checked, and only then do the columns go.
--
-- WHAT THIS STEP IS, AND HOW IT DIFFERS FROM 0002. `0002_progress_notes_backfill.sql` is additive: it
-- copies the column's notes into the ledger and leaves `progress_history` and `progress_count` where
-- they are, which is what keeps the union read correct while the switch is half landed. This step is
-- the one NEXT_GEN's O1c box and D1 3a rule, and its difference is that it DESTROYS the source: it
-- carries, it CHECKS the carry, and only then drops the two columns on both tables. All of it is one
-- transaction, because the runner holds each step in its own - so a failure here leaves the columns
-- intact and records no `applied_migrations` row.
--
-- IT CARRIES THE SAME WAY 0002 DOES, ON PURPOSE. The payload is exactly what `0002` wrote and what
-- application/services/task_event_recorder.go's RecordProgress writes for a live note - content (the
-- text WITH its numbered header, as the column stores it), progress_number, timestamp - plus
-- `carried_from`, the column key it was copied from. `ProgressTextWith` merges on content +
-- progress_number, which is why a note 0002 already carried is NOT carried twice here: the NOT EXISTS
-- guard skips it, and this step's own count check is therefore about the ledger HOLDING every entry,
-- not about this step having inserted them. That is also what makes the step safe on a database where
-- 0002 ran, and identical in effect on one where it did not.
--
-- A MALFORMED ENTRY FAILS THE STEP, WHERE 0002 SKIPS IT. That difference is the point of the ruling: a
-- note this step cannot read is a note it is about to destroy, so the honest outcome is a failed step
-- and an intact column (`NEXT_GEN.md`'s O1c check: "a malformed entry -> step fails, column intact"),
-- never a dropped column and a lost note. An entry without content, without a progress_number, or
-- without a timestamp raises below; 0002 could afford to skip them because it destroyed nothing.
--
-- WHY `human` AND NOT A NEW ACTOR KIND. The ledger's actor_kind vocabulary is closed ('seat',
-- 'client', 'gate', 'human') and a carried note was written by the user the row belongs to, before any
-- seat attributed writes, so attributing it to that user is the truthful value. Inventing a 'carry'
-- actor would widen a closed vocabulary to describe the migration rather than the note.
--
-- LOCKED AGAINST LIVE APPENDS. The runner holds its own advisory lock, but an append takes the
-- per-user lock in TaskEventRepository.AppendInTx, which is a different key: without this the MAX+1
-- numbering below could race a live append and either side could collide on the uniques. The lock
-- statement below takes each affected user's lock for the rest of this transaction, in the same key
-- the append path uses.

-- THE BASELINE MARK IS CHECKED HERE, NOT ASSUMED. This step destroys its source, and until this block
-- existed nothing tied it to the owner's mark: validateSet checks a set's names, order and duplicates,
-- never a step's provenance, so a database where 0001 was SKIPPED - which is what the runner with the
-- inert baseline does whenever the catalogue is not empty, i.e. every boot - reached the DROP below
-- with no 0001_baseline row and no owner action. The ordering rule is
-- ARCH-RULING-0001-baseline-canonicity: the mark is Runner.MarkBaseline("0001_baseline"), an owner
-- action, and this refuses until it is there. The raise rolls this step's OWN transaction back
-- (migration_runner.go applies each step in one), so both columns stay and no applied_migrations row
-- is written.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM applied_migrations WHERE migration_name = '0001_baseline') THEN
        RAISE EXCEPTION 'the O1c carry step runs only under the owner''s 0001 baseline mark; run Runner.MarkBaseline(''0001_baseline'') first';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtext(u.user_id::text))
FROM (
    SELECT DISTINCT user_id FROM tasks
    UNION
    SELECT DISTINCT user_id FROM subtasks
) AS u;

-- The stored entries, read once. A temp table rather than a CTE because the carry and both checks
-- need the same set, and a CTE does not outlive its statement; ON COMMIT DROP ties its life to this
-- step's transaction, which the runner commits or rolls back as a whole.
CREATE TEMP TABLE progress_carry_entries ON COMMIT DROP AS
SELECT t.user_id,
       t.id                      AS task_id,
       NULL::uuid                AS subtask_id,
       e.key                     AS col_key,
       (e.value ->> 'content')   AS content,
       (e.value ->> 'progress_number')::double precision AS number,
       (e.value ->> 'timestamp') AS ts
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
       (e.value ->> 'timestamp')
FROM subtasks s
CROSS JOIN LATERAL jsonb_each(to_jsonb(s.progress_history)) AS e(key, value)
WHERE jsonb_typeof(to_jsonb(s.progress_history)) = 'object';

-- An entry the ledger cannot express raises here, before anything is dropped. This is the check 0002
-- documents that it deliberately does NOT have.
DO $$
DECLARE
    incomplete integer;
BEGIN
    SELECT count(*) INTO incomplete
    FROM progress_carry_entries e
    WHERE e.content IS NULL
       OR e.number IS NULL
       OR e.ts IS NULL
       OR e.ts = '';

    IF incomplete > 0 THEN
        RAISE EXCEPTION
            'the carry cannot express % progress entr(ies) that have no content, progress_number or timestamp; progress_history is left intact',
            incomplete;
    END IF;
END $$;

WITH user_tip AS (
    SELECT user_id, COALESCE(MAX(user_seq), 0) AS base FROM task_events GROUP BY user_id
),
task_tip AS (
    SELECT user_id, task_id, COALESCE(MAX(seq), 0) AS base FROM task_events GROUP BY user_id, task_id
),
missing AS (
    SELECT e.*
    FROM progress_carry_entries e
    WHERE NOT EXISTS (
        SELECT 1
        FROM task_events te
        WHERE te.user_id = e.user_id
          AND te.task_id = e.task_id
          AND te.kind = 'progress'
          AND (te.payload ->> 'progress_number')::double precision = e.number
          AND (te.payload ->> 'content') = e.content
          AND te.subtask_id IS NOT DISTINCT FROM e.subtask_id
    )
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

-- The carry is CHECKED before the source is destroyed. One ledger row per entry, under the identity
-- the reader merges on: content and progress_number together. A number held by a DIFFERENT content is
-- a collision rather than a match, and it fails here - dropping the column would erase a note the
-- ledger does not actually hold.
DO $$
DECLARE
    unheld     integer;
    mismatched integer;
BEGIN
    SELECT count(*) INTO unheld
    FROM progress_carry_entries e
    WHERE NOT EXISTS (
        SELECT 1
        FROM task_events te
        WHERE te.user_id = e.user_id
          AND te.task_id = e.task_id
          AND te.kind = 'progress'
          AND (te.payload ->> 'progress_number')::double precision = e.number
          AND (te.payload ->> 'content') = e.content
          AND te.subtask_id IS NOT DISTINCT FROM e.subtask_id
    );

    IF unheld > 0 THEN
        RAISE EXCEPTION
            'the ledger holds no progress event for % of the entries about to be dropped; progress_history is left intact',
            unheld;
    END IF;

    SELECT count(*) INTO mismatched
    FROM progress_carry_entries e
    JOIN task_events te
      ON te.user_id = e.user_id
     AND te.task_id = e.task_id
     AND te.kind = 'progress'
     AND (te.payload ->> 'progress_number')::double precision = e.number
     AND te.subtask_id IS NOT DISTINCT FROM e.subtask_id
    WHERE (te.payload ->> 'content') <> e.content;

    IF mismatched > 0 THEN
        RAISE EXCEPTION
            'progress_number is held by a ledger event whose content differs from the column''s, for % entr(ies); progress_history is left intact',
            mismatched;
    END IF;
END $$;

-- Only now, with the carry in the ledger and checked, does the source go. Both tables, both columns:
-- `progress_count` is the column's own bookkeeping and has no other reader.
ALTER TABLE tasks DROP COLUMN progress_history;
ALTER TABLE tasks DROP COLUMN progress_count;
ALTER TABLE subtasks DROP COLUMN progress_history;
ALTER TABLE subtasks DROP COLUMN progress_count;
