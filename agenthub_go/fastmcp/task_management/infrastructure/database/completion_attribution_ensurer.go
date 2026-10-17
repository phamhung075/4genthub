package database

// tasks gained completed_by (the seat whose completion line the row holds) AFTER the table already
// existed in every live database. createAll creates a table only when it is ABSENT, so without an
// ensurer the column would exist everywhere except a database that already holds the table - the same
// trap acceptance_criteria and scope are recorded against in acceptance_scope_ensurer.go, which this
// file follows.
//
// The statement is the TableDef's shape (models.go): VARCHAR, NOT NULL, DEFAULT ''. A one-row-rewrite
// default, so an existing completed task answers '' - "no recorded author" - rather than inventing
// one, and the completion gate in complete_task.go treats that as needing an explicit correction.
//
// Idempotent by IF NOT EXISTS (the seam's requirement), and it runs only under AUTO_MIGRATE=true.

import (
	"context"
	"database/sql"
)

// EnsureTaskCompletedByColumn adds tasks.completed_by on a database that already holds the table.
func EnsureTaskCompletedByColumn(ctx context.Context, db *sql.DB) error {
	_, err := db.ExecContext(ctx,
		"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_by VARCHAR NOT NULL DEFAULT ''")
	return err
}

func init() {
	ColumnEnsurers = append(ColumnEnsurers, EnsureTaskCompletedByColumn)
}
