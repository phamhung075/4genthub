package database

// tasks and subtasks gained acceptance_criteria and scope (JSON string arrays, O4 slice 1) AFTER
// both tables already existed in every live database. createAll creates a table only when it is
// ABSENT, so without an ensurer the two columns would exist everywhere except a database that
// already holds the table - the same trap the task_events.user_seq incident is recorded against.
// This file is the path such a database takes; a FRESH one gets the columns from the tasks/subtasks
// TableDefs (models.go) and the embedded init_schema_postgresql.sql.
//
// The delta is a hand-written pair of statements rather than a call to EnsureTableColumns,
// DELIBERATELY. That helper derives the column half of the WHOLE table and ends with a verify pass
// over every column, and several tasks/subtasks columns carry a JSON ServerDefault ("{}" / "[]")
// that addColumnSQL would emit verbatim as a DEFAULT literal: harmless while the column already
// exists (ADD COLUMN IF NOT EXISTS skips it), a parse error the moment one did not. Two guarded
// ADD COLUMNs touch only the columns this row is about.
//
// The type is the TableDef's, not the embedded schema's JSONB - the same choice EnsureAIColumnsExist
// makes - so a database that takes this path converges on the shape createAll builds.
//
// It is idempotent by IF NOT EXISTS (the seam's requirement), so a repeated boot changes nothing.
// NOT NULL with DEFAULT '[]' gives an existing row '[]' without a rewrite, so no ColumnDataMove is
// needed. It runs only under AUTO_MIGRATE=true: CreateTables is the ensurers' only caller, and
// InitDatabase reaches it only under that opt-in.

import (
	"context"
	"database/sql"
)

// taskAcceptanceScopeStatements add the two columns to one table. Both are guarded so a fresh
// database, where createAll has already created them, is left alone.
func taskAcceptanceScopeStatements(table string) []string {
	return []string{
		"ALTER TABLE " + table + " ADD COLUMN IF NOT EXISTS acceptance_criteria JSON NOT NULL DEFAULT '[]'",
		"ALTER TABLE " + table + " ADD COLUMN IF NOT EXISTS scope JSON NOT NULL DEFAULT '[]'",
	}
}

// EnsureTaskAcceptanceScopeColumns adds acceptance_criteria and scope to tasks and subtasks on a
// database that already holds the tables. All four statements run in one transaction: a database
// either ends up with both columns on both tables or is left exactly as it was.
func EnsureTaskAcceptanceScopeColumns(ctx context.Context, db *sql.DB) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	for _, table := range []string{"tasks", "subtasks"} {
		for _, stmt := range taskAcceptanceScopeStatements(table) {
			if _, err := tx.ExecContext(ctx, stmt); err != nil {
				_ = tx.Rollback()
				return err
			}
		}
	}
	return tx.Commit()
}

func init() {
	ColumnEnsurers = append(ColumnEnsurers, EnsureTaskAcceptanceScopeColumns)
}
