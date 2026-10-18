package database_test

// THE UPGRADE PATH, on a real database: a database that predates the columns the boot used to patch
// in must gain them from the embedded steps alone. This is the half of the single-creator ruling
// (seat-tier decision 2026-10-17 22:45Z) that a fresh-database boot cannot show: 0001 is skipped on a
// database whose catalogue already holds tables, so only 0005/0006 can reach it.
//
// THE SIMULATION, and why it is honest. A legacy database is one whose ledger does not record
// 0005/0006 and whose tables lack the columns those steps add. The case builds exactly that: it boots
// the schema, drops a representative column of each former ensurer, deletes those two ledger rows -
// which is what "this database predates the steps" means to the runner - and boots again. Every column
// must be back, the task_events numbering must be gapless per user, and the second boot must change
// nothing more (a repeated boot is a no-op).
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"database/sql"
	"strconv"
	"testing"

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// legacyDroppedColumns is one column per former ensurer, with the table that must carry it again.
var legacyDroppedColumns = []struct{ table, column string }{
	{"tasks", "acceptance_criteria"},
	{"tasks", "completed_by"},
	{"tasks", "ai_system_prompt"},
	{"agent_sessions", "room_slug"},
	{"agent_sessions", "client_cursor"},
	{"rooms", "team_id"},
	{"room_decisions", "acked_at"},
	{"task_events", "client_event_id"},
	{"task_events", "user_seq"},
}

func columnOn(t *testing.T, db *sql.DB, table, column string) bool {
	t.Helper()
	var exists bool
	if err := db.QueryRowContext(context.Background(),
		`SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=$1 AND column_name=$2)`,
		table, column).Scan(&exists); err != nil {
		t.Fatalf("column %s.%s: %v", table, column, err)
	}
	return exists
}

func TestALegacyDatabaseGainsThePatchedColumnsFromTheSteps(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db}}
	testdb.CreateSchema(t, cfg)

	// THE EVENTS ARE SEEDED BEFORE user_seq IS DROPPED, so the step's backfill has rows to number: the
	// drop loses the values, and the upgrade must number them per user, in (created_at, id) order.
	const (
		taskID = "bbbb1111-0000-4000-8000-0000000000bb"
		userID = "user-legacy"
	)
	// A task the schema's own NOT NULL columns accept: the events below hang off it.
	if _, err := db.ExecContext(ctx, `INSERT INTO projects (id, name, description, created_at, updated_at, user_id, status, metadata)
		VALUES ('dddd1111-0000-4000-8000-0000000000dd', 'legacy', '', now(), now(), $1, 'active', '{}')`, userID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ('eeee1111-0000-4000-8000-0000000000ee', 'dddd1111-0000-4000-8000-0000000000dd', 'legacy', '', now(), now(), 'medium', 'todo', '{}', 0, 0, $1)`, userID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `INSERT INTO tasks (id, status, priority, user_id, title, description, git_branch_id, estimated_effort, completion_summary, testing_notes, progress_percentage, progress_state, created_at, updated_at)
		VALUES ($1, 'todo', 'medium', $2, 'legacy', '', 'eeee1111-0000-4000-8000-0000000000ee', '', '', '', 0, 'INITIAL', now(), now())`, taskID, userID); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 3; i++ {
		if _, err := db.ExecContext(ctx, `INSERT INTO task_events (id, task_id, user_id, seq, user_seq, kind, actor_kind, actor_id, created_at)
			VALUES (gen_random_uuid(), $1, $2, $3, $4, 'progress', 'seat', 'go-dev', now() + ($5 || ' seconds')::interval)`,
			taskID, userID, i+1, 100+i, strconv.Itoa(i)); err != nil {
			t.Fatalf("seed event %d: %v", i, err)
		}
	}

	for _, c := range legacyDroppedColumns {
		if !columnOn(t, db, c.table, c.column) {
			t.Fatalf("the fresh boot is missing %s.%s, so this case would prove nothing", c.table, c.column)
		}
		if _, err := db.ExecContext(ctx, `ALTER TABLE `+c.table+` DROP COLUMN `+c.column); err != nil {
			t.Fatalf("drop %s.%s: %v", c.table, c.column, err)
		}
	}
	if _, err := db.ExecContext(ctx,
		`DELETE FROM applied_migrations WHERE migration_name IN ('0005_patch_columns_the_boot_added','0006_task_event_vocabularies')`); err != nil {
		t.Fatalf("forget the two steps: %v", err)
	}

	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("the upgrade boot failed: %v", err)
	}
	for _, c := range legacyDroppedColumns {
		if !columnOn(t, db, c.table, c.column) {
			t.Errorf("the step did not restore %s.%s", c.table, c.column)
		}
	}

	// THE BACKFILL: three rows for one user, numbered 1..3 in (created_at, id) order - never restarting
	// above a value that survived, and never leaving a NULL behind the NOT NULL the same step sets.
	rows, err := db.QueryContext(ctx, `SELECT user_seq FROM task_events WHERE user_id = $1 ORDER BY user_seq`, userID)
	if err != nil {
		t.Fatal(err)
	}
	var numbered []int
	for rows.Next() {
		var n sql.NullInt64
		if err := rows.Scan(&n); err != nil {
			t.Fatal(err)
		}
		if !n.Valid {
			t.Fatal("a task_events row carries no user_seq after the step")
		}
		numbered = append(numbered, int(n.Int64))
	}
	rows.Close()
	if len(numbered) != 3 || numbered[0] != 1 || numbered[1] != 2 || numbered[2] != 3 {
		t.Fatalf("user_seq after the backfill = %v, want 1,2,3", numbered)
	}

	before := countRows(t, db, "applied_migrations")
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("a repeated boot failed: %v", err)
	}
	if after := countRows(t, db, "applied_migrations"); after != before {
		t.Fatalf("a repeated boot applied %d more steps", after-before)
	}
}

func countRows(t *testing.T, db *sql.DB, table string) int {
	t.Helper()
	var n int
	if err := db.QueryRowContext(context.Background(), `SELECT count(*) FROM `+table).Scan(&n); err != nil {
		t.Fatal(err)
	}
	return n
}
