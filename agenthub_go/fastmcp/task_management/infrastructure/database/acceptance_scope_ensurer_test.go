package database_test

// O4 slice 1's column half: tasks and subtasks gained acceptance_criteria and scope AFTER both
// tables already existed in every live database. createAll creates a table only when it is ABSENT, so
// on a fresh database the columns come from the TableDefs and this fixture cannot tell whether the
// ensurer carries them anywhere. The failure lives in the UPGRADE path - the shape a database that
// already holds the tables has - so the case below DROPS the columns from a database built by the
// production path and asks the ensurer to put them back, which is exactly what it exists for.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"database/sql"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// acceptanceScopeColumn reads one column back out of the catalogue: present, its reported type,
// whether it is NOT NULL, and its default expression.
func acceptanceScopeColumn(t *testing.T, db *sql.DB, table, column string) (present bool, typ string, notNull bool, def string) {
	t.Helper()
	err := db.QueryRowContext(context.Background(), `
		SELECT format_type(a.atttypid, a.atttypmod), a.attnotnull, COALESCE(pg_get_expr(d.adbin, d.adrelid), '')
		  FROM pg_attribute a
		  JOIN pg_class c ON c.oid = a.attrelid
		  LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
		 WHERE c.relname = $1 AND a.attname = $2 AND a.attnum > 0 AND NOT a.attisdropped`, table, column).
		Scan(&typ, &notNull, &def)
	if err == sql.ErrNoRows {
		return false, "", false, ""
	}
	if err != nil {
		t.Fatalf("reading %s.%s from the catalogue: %v", table, column, err)
	}
	return true, typ, notNull, def
}

// TestAcceptanceScopeColumnsExistOnAFreshDatabase pins the shape createAll builds: both columns on
// both tables, NOT NULL with default '[]', so the ensurer below is a no-op there rather than the
// thing that hides a missing TableDef.
func TestAcceptanceScopeColumnsExistOnAFreshDatabase(t *testing.T) {
	_, db := newMigrationRunnerEnv(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	for _, table := range []string{"tasks", "subtasks"} {
		for _, column := range []string{"acceptance_criteria", "scope"} {
			present, typ, notNull, def := acceptanceScopeColumn(t, db, table, column)
			if !present {
				t.Fatalf("%s.%s is missing on a fresh database, so the TableDef/DDL path did not carry it", table, column)
			}
			if typ != "json" {
				t.Errorf("%s.%s has type %s, want json (the TableDef's type)", table, column, typ)
			}
			if !notNull {
				t.Errorf("%s.%s is nullable, want NOT NULL", table, column)
			}
			if def != "'[]'::json" {
				t.Errorf("%s.%s default = %q, want '[]'::json", table, column, def)
			}
		}
	}
}

// TestAcceptanceScopeEnsurerRestoresAnOldShapeWithRows is the case the ensurer exists for. A
// populated database is left without the two columns - the shape that predates them - and the
// ensurer has to give every existing row '[]' without rewriting the table, then make the columns
// NOT NULL. A second run must apply nothing, which is the seam's idempotence requirement.
func TestAcceptanceScopeEnsurerRestoresAnOldShapeWithRows(t *testing.T) {
	_, db := newMigrationRunnerEnv(t)
	ctx := context.Background()

	// A row in each table, written while the columns still exist so the tables are POPULATED when
	// the columns are dropped - the shape an existing database has.
	mustExec(t, db, `INSERT INTO projects (id, name, description, user_id, status, metadata, created_at, updated_at)
		VALUES ('11111111-1111-4111-8111-111111111111', 'p', '', 'u', 'active', '{}', now(), now())`)
	mustExec(t, db, `INSERT INTO project_git_branchs (id, project_id, name, description, user_id, priority, status, metadata, task_count, completed_task_count, created_at, updated_at)
		VALUES ('22222222-2222-4222-8222-222222222222', '11111111-1111-4111-8111-111111111111', 'main', '', 'u', 'medium', 'todo', '{}', 0, 0, now(), now())`)
	mustExec(t, db, `INSERT INTO tasks (id, title, description, git_branch_id, status, priority, progress_history, progress_count,
			estimated_effort, created_at, updated_at, completion_summary, testing_notes, progress_percentage, progress_state, user_id)
		VALUES ('33333333-3333-4333-8333-333333333333', 't', 'd', '22222222-2222-4222-8222-222222222222', 'todo', 'medium', '{}', 0,
			'2 hours', now(), now(), '', '', 0, 'INITIAL', 'u')`)
	mustExec(t, db, `INSERT INTO subtasks (id, task_id, title, description, status, priority, assignees, progress_percentage, progress_history,
			progress_count, progress_state, progress_notes, blockers, completion_summary, impact_on_parent, insights_found, user_id, created_at, updated_at)
		VALUES ('44444444-4444-4444-8444-444444444444', '33333333-3333-4333-8333-333333333333', 's', '', 'todo', 'medium', '[]', 0, '{}',
			0, 'INITIAL', '', '', '', '', '[]', 'u', now(), now())`)

	for _, table := range []string{"tasks", "subtasks"} {
		mustExec(t, db, "ALTER TABLE "+table+" DROP COLUMN acceptance_criteria, DROP COLUMN scope")
		if present, _, _, _ := acceptanceScopeColumn(t, db, table, "acceptance_criteria"); present {
			t.Fatalf("%s.acceptance_criteria survived the drop, so the fixture is not the old shape", table)
		}
	}

	if err := database.EnsureTaskAcceptanceScopeColumns(ctx, db); err != nil {
		t.Fatalf("the ensurer failed on a database that lacks the columns: %v", err)
	}

	for _, table := range []string{"tasks", "subtasks"} {
		present, typ, notNull, def := acceptanceScopeColumn(t, db, table, "acceptance_criteria")
		if !present || typ != "json" || !notNull || def != "'[]'::json" {
			t.Errorf("%s.acceptance_criteria after the ensurer: present=%v type=%s notNull=%v default=%q, want present json true '[]'::json",
				table, present, typ, notNull, def)
		}
		present, typ, notNull, def = acceptanceScopeColumn(t, db, table, "scope")
		if !present || typ != "json" || !notNull || def != "'[]'::json" {
			t.Errorf("%s.scope after the ensurer: present=%v type=%s notNull=%v default=%q, want present json true '[]'::json",
				table, present, typ, notNull, def)
		}
	}

	// The rows written before the drop carry '[]', not NULL, because the column is NOT NULL with a
	// default - ADD COLUMN fills the existing rows rather than refusing them.
	for _, tc := range []struct{ table, id string }{
		{"tasks", "33333333-3333-4333-8333-333333333333"},
		{"subtasks", "44444444-4444-4444-8444-444444444444"},
	} {
		var criteria, scope string
		if err := db.QueryRowContext(ctx, "SELECT acceptance_criteria::text, scope::text FROM "+tc.table+" WHERE id = $1::uuid", tc.id).
			Scan(&criteria, &scope); err != nil {
			t.Fatalf("reading the restored columns of %s: %v", tc.table, err)
		}
		if criteria != "[]" || scope != "[]" {
			t.Errorf("%s's pre-existing row got acceptance_criteria=%s scope=%s, want [] []", tc.table, criteria, scope)
		}
	}

	// A second run applies nothing and does not fail.
	if err := database.EnsureTaskAcceptanceScopeColumns(ctx, db); err != nil {
		t.Fatalf("the ensurer is not idempotent: a second run failed: %v", err)
	}
	if present, _, _, _ := acceptanceScopeColumn(t, db, "tasks", "scope"); !present {
		t.Fatal("scope disappeared on the second run")
	}
}

func mustExec(t *testing.T, db *sql.DB, stmt string) {
	t.Helper()
	if _, err := db.ExecContext(context.Background(), stmt); err != nil {
		t.Fatalf("exec %q: %v", stmt, err)
	}
}
