package database

// task_events' P1 delta postdates its table, so it ships on BOTH paths the column seam requires -
// the same shape session_stream's session_columns.go documents: this ensurer for a database that
// ALREADY holds the table, and the task_events TableDef (task_event_tables.go) for a fresh one.
// createAll creates a table only when it is ABSENT, so without this the delta would exist everywhere
// except the database that already had the table - which is exactly what production did: every
// status write goes through the recorder, the recorder writes user_seq, and the write failed with
// `column "user_seq" does not exist` while /health kept answering. The definition has FOUR parts,
// not one, and a repair that adds only the first leaves the write path failing on the next:
//
//  1. user_seq BIGINT NOT NULL with uq_task_event_user_seq UNIQUE (user_id, user_seq)
//  2. client_event_id UUID, nullable, with uq_task_event_client_event UNIQUE (user_id, client_event_id)
//  3. ck_task_event_kind widened to the twelve-kind vocabulary
//  4. ck_task_event_actor_kind widened to seat|client|gate|human
//
// Parts 3 and 4 are on the write path too, and that is not theoretical: the recorder stamps
// actor_kind 'seat' and the ledger's own next writers emit kinds the five-kind vocabulary never had,
// so on a database carrying the OLD checks a status write is refused by the actor check and a
// progress entry by the kind check. The vocabulary in both checks is the TableDef's, and
// TestEnsureTaskEventColumnsMatchTheDefinition compares these lists against the TableDef's DDL so a
// later vocabulary change cannot leave this file behind.
//
// WHY THE SHAPES ARE GUARDED RATHER THAN PLAIN. CreateTables runs createAll FIRST and the ensurers
// after it (database_config.go), so on a FRESH database the columns, the uniques and the widened
// checks already exist: a plain ADD COLUMN or ADD CONSTRAINT would fail every fresh boot and every
// database-backed test. Hence ADD COLUMN IF NOT EXISTS, a backfill that touches only rows where
// user_seq IS NULL, SET NOT NULL after it, and every constraint re-created as DROP IF EXISTS then
// ADD (the seam's own precedent), which is a no-op when the definition already matches.
//
// THE BACKFILL NUMBERS PER USER, IN (created_at, id) ORDER, ABOVE THAT USER'S CURRENT MAXIMUM. A
// gapless per-user sequence is what the table's cursor and outbox need (uq_task_event_user_seq is
// what keeps the read cursor from repeating), so the numbering must not restart at 1 above rows
// that already carry a value - an existing database may have had the column added by hand, and a
// collision there would fail the constraint the same statement is about to create. This is reading
// R1 of the lead's ruling: production ends up EQUAL to the Go definition, nothing moves between
// tables and nothing is dropped.
//
// It runs only under AUTO_MIGRATE=true: CreateTables is the ensurers' only caller
// (task_management/infrastructure/database/database_config.go, reached from InitDatabase only under
// that opt-in). Under AUTO_MIGRATE=false NOTHING here runs, the columns are never added, and the
// status/event write path keeps failing exactly as it does now - the opt-in is load-bearing, not
// cosmetic.

import (
	"context"
	"database/sql"
)

// The two vocabularies, verbatim from the TableDef's CHECK clauses. TestEnsureTaskEventColumnsMatch-
// TheDefinition fails if they stop agreeing with task_event_tables.go.
const (
	taskEventKindVocabulary      = "'assigned', 'claimed', 'delivered', 'context_loaded', 'progress', 'status_changed', 'evidence_submitted', 'gate_verdict', 'escalated', 'human_decision', 'handover', 'context_updated'"
	taskEventActorKindVocabulary = "'seat', 'client', 'gate', 'human'"
)

// The statements are split so a reader can see which shape guards what, and they run in ONE
// transaction: a database either ends up with the whole delta or it is left exactly as it was.
var taskEventDefinitionStatements = []string{
	// 1. the per-user sequence: nullable first, backfilled, then NOT NULL, then unique.
	"ALTER TABLE task_events ADD COLUMN IF NOT EXISTS user_seq BIGINT",
	`UPDATE task_events e SET user_seq = numbered.rn FROM (
		SELECT t.id,
		       COALESCE((SELECT MAX(m.user_seq) FROM task_events m WHERE m.user_id = t.user_id), 0)
		       + ROW_NUMBER() OVER (PARTITION BY t.user_id ORDER BY t.created_at, t.id) AS rn
		FROM task_events t WHERE t.user_seq IS NULL
	) numbered WHERE e.id = numbered.id`,
	"ALTER TABLE task_events ALTER COLUMN user_seq SET NOT NULL",
	// 2. the outbox key: nullable by definition, so there is nothing to backfill - NULL is the
	// honest value for a row that never carried the caller's idempotency key, and the unique index
	// treats NULLs as distinct.
	"ALTER TABLE task_events ADD COLUMN IF NOT EXISTS client_event_id UUID",
}

// The two closed vocabularies are re-created from the definition rather than widened in place. They
// run in their own transaction because this step validates every existing row (see
// EnsureTaskEventColumns).
var taskEventVocabularyStatements = []string{
	"ALTER TABLE task_events DROP CONSTRAINT IF EXISTS ck_task_event_kind",
	"ALTER TABLE task_events ADD CONSTRAINT ck_task_event_kind CHECK (kind IN (" + taskEventKindVocabulary + "))",
	"ALTER TABLE task_events DROP CONSTRAINT IF EXISTS ck_task_event_actor_kind",
	"ALTER TABLE task_events ADD CONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN (" + taskEventActorKindVocabulary + "))",
}

// The two uniques are added inside DO blocks that check pg_constraint, because a plain ADD
// CONSTRAINT fails on a fresh database where createAll has already created them.
var taskEventUniqueStatements = []string{
	`DO $$ BEGIN
		IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_task_event_user_seq') THEN
			ALTER TABLE task_events ADD CONSTRAINT uq_task_event_user_seq UNIQUE (user_id, user_seq);
		END IF;
	END $$`,
	`DO $$ BEGIN
		IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_task_event_client_event') THEN
			ALTER TABLE task_events ADD CONSTRAINT uq_task_event_client_event UNIQUE (user_id, client_event_id);
		END IF;
	END $$`,
}

// EnsureTaskEventColumns adds everything task_events gained after P1 to a database that already
// holds the table: the per-user sequence (backfilled), the outbox key, and the widened kind and
// actor vocabularies.
//
// THE COLUMNS AND THE WIDENINGS RUN IN TWO TRANSACTIONS ON PURPOSE. The columns can be added to ANY
// table, so they must land even where the widenings cannot: recreating a CHECK validates every
// existing row, and a table whose rows carry the OLD vocabulary (user|system|agent) cannot satisfy
// the new one without rewriting those values - a data move, which the incident's order forbade. With
// both in one transaction that table would get no repair at all and the boot would fail on a
// constraint rather than on the missing column it actually has. Split, such a database gets its
// columns and the second step fails LOUDLY with the constraint's own message, which names the values
// an operator has to migrate deliberately. On the real ledger this cannot arise: nothing wrote
// task_events before P1's reader landed, so the table the widening meets is empty.
func EnsureTaskEventColumns(ctx context.Context, db *sql.DB) error {
	if err := applyTaskEventStatements(ctx, db, append(append([]string{}, taskEventDefinitionStatements...), taskEventUniqueStatements...)); err != nil {
		return err
	}
	return applyTaskEventStatements(ctx, db, taskEventVocabularyStatements)
}

// applyTaskEventStatements runs statements in one transaction: a database either ends up with all of
// them or is left exactly as it was.
func applyTaskEventStatements(ctx context.Context, db *sql.DB, statements []string) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	for _, stmt := range statements {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func init() {
	ColumnEnsurers = append(ColumnEnsurers, EnsureTaskEventColumns)
}
