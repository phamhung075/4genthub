package database

// Automatic Database Migration Runner (Python
// task_management/infrastructure/database/auto_migration.py).
//
// Deviations: the SQLite fallback statements and the SQLAlchemy error taxonomy are not
// ported (the Go database is always PostgreSQL); per-statement errors that Python catches
// and logs are swallowed the same way. The UPDATE ... ::progressstate cast is kept verbatim,
// including the fact that it fails when the enum type is missing.

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
)

// AutoMigration runs the startup migrations Python performs.
type AutoMigration struct {
	ctx context.Context
	db  *sql.DB
}

// NewAutoMigration builds a migration runner over a PostgreSQL handle.
func NewAutoMigration(ctx context.Context, db *sql.DB) *AutoMigration {
	return &AutoMigration{ctx: ctx, db: db}
}

// RunAutoMigrations is the module-level run_auto_migrations entry point.
func RunAutoMigrations(ctx context.Context, db *sql.DB) bool {
	return NewAutoMigration(ctx, db).RunAllMigrations()
}

// RunAllMigrations runs every migration; a failing step aborts the remainder, like Python.
// Without AUTO_MIGRATE=true it is a no-op that reports success.
func (a *AutoMigration) RunAllMigrations() bool {
	if !autoMigrateEnabled() {
		return true
	}
	if err := a.renameSubtasksTable(); err != nil {
		return false
	}
	if err := a.addProgressStateColumns(); err != nil {
		return false
	}
	if err := a.addSubtaskCountColumn(); err != nil {
		return false
	}
	return true
}

// renameSubtasksTable renames task_subtasks to subtasks when needed; driver errors are
// swallowed (Python catches OperationalError).
func (a *AutoMigration) renameSubtasksTable() error {
	tables, err := tableNames(a.ctx, a.db)
	if err != nil {
		return err
	}
	if contains(tables, "task_subtasks") && !contains(tables, "subtasks") {
		if _, err := a.db.ExecContext(a.ctx, "ALTER TABLE task_subtasks RENAME TO subtasks"); err != nil {
			return nil
		}
	}
	return nil
}

// addProgressStateColumns adds and back-fills progress_state on tasks and subtasks.
func (a *AutoMigration) addProgressStateColumns() error {
	tables, err := tableNames(a.ctx, a.db)
	if err != nil {
		return err
	}
	for _, table := range []string{"tasks", "subtasks"} {
		if !contains(tables, table) {
			continue
		}
		columns, err := columnNames(a.ctx, a.db, table)
		if err != nil {
			// Python rolls back and skips the table.
			continue
		}
		if !contains(columns, "progress_state") {
			if _, err := a.db.ExecContext(a.ctx, fmt.Sprintf(
				"ALTER TABLE %s ADD COLUMN progress_state VARCHAR(20) DEFAULT 'INITIAL' NOT NULL", table)); err != nil {
				// Column might already exist; Python rolls back and continues.
				_ = err
			}
		}
		_, _ = a.db.ExecContext(a.ctx, fmt.Sprintf(`
                            UPDATE %s
                            SET progress_state = (CASE
                                WHEN status = 'done' THEN 'COMPLETE'
                                WHEN status IN ('in_progress', 'active') THEN 'IN_PROGRESS'
                                ELSE 'INITIAL'
                            END)::progressstate
                            WHERE progress_state = 'INITIAL'
                        `, table))
	}
	return nil
}

// addSubtaskCountColumn adds subtask_count to tasks.
func (a *AutoMigration) addSubtaskCountColumn() error {
	tables, err := tableNames(a.ctx, a.db)
	if err != nil {
		return err
	}
	if !contains(tables, "tasks") {
		return nil
	}
	columns, err := columnNames(a.ctx, a.db, "tasks")
	if err != nil {
		return nil
	}
	if contains(columns, "subtask_count") {
		return nil
	}
	_, err = a.db.ExecContext(a.ctx, "ALTER TABLE tasks ADD COLUMN subtask_count INTEGER DEFAULT 0")
	if err != nil && !isDuplicateColumnErr(err) {
		return err
	}
	return nil
}

func isDuplicateColumnErr(err error) bool {
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "duplicate column") || strings.Contains(msg, "already exists")
}
