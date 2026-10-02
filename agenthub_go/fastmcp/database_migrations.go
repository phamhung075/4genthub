package fastmcp

// Database migration runner (Python fastmcp/database_migrations.py): applies the
// progress_history/progress_count migration and the uuid-ossp extension on startup. Only the
// PostgreSQL branch is ported; the non-PostgreSQL URL check is kept as a fast return.

import (
	"context"
	"strings"
	"sync"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// DatabaseMigrator handles database migrations for the application.
type DatabaseMigrator struct {
	DatabaseURL string
}

// NewDatabaseMigrator builds the URL from the argument or the environment.
func NewDatabaseMigrator(databaseURL string) *DatabaseMigrator {
	if databaseURL != "" {
		return &DatabaseMigrator{DatabaseURL: databaseURL}
	}
	return &DatabaseMigrator{DatabaseURL: buildDatabaseURLFromEnv()}
}

// RunMigrations applies the tasks progress migration; any error returns false.
func (m *DatabaseMigrator) RunMigrations() bool {
	if !strings.Contains(m.DatabaseURL, "postgresql") {
		return true
	}
	db, err := database.PgxOpener(m.DatabaseURL, database.EngineOptions{})
	if err != nil {
		return false
	}
	defer db.Close()
	ctx := context.Background()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return false
	}
	var tableExists bool
	if err := tx.QueryRowContext(ctx, `SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'tasks'
                        );`).Scan(&tableExists); err != nil {
		_ = tx.Rollback()
		return false
	}
	if !tableExists {
		_ = tx.Commit()
		return true
	}
	rows, err := tx.QueryContext(ctx, `SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'tasks'
                        AND column_name IN ('progress_history', 'progress_count', 'details');`)
	if err != nil {
		_ = tx.Rollback()
		return false
	}
	existingColumns := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			rows.Close()
			_ = tx.Rollback()
			return false
		}
		existingColumns[name] = true
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		_ = tx.Rollback()
		return false
	}
	rows.Close()

	if !existingColumns["progress_history"] {
		if _, err := tx.ExecContext(ctx, `ALTER TABLE tasks
                            ADD COLUMN progress_history JSON DEFAULT '{}';`); err != nil {
			_ = tx.Rollback()
			return false
		}
	}
	if !existingColumns["progress_count"] {
		if _, err := tx.ExecContext(ctx, `ALTER TABLE tasks
                            ADD COLUMN progress_count INTEGER DEFAULT 0;`); err != nil {
			_ = tx.Rollback()
			return false
		}
	}
	if existingColumns["details"] {
		var countToMigrate int
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM tasks
                            WHERE details IS NOT NULL
                            AND (progress_history IS NULL OR progress_history::text = '{}');`).Scan(&countToMigrate); err != nil {
			_ = tx.Rollback()
			return false
		}
		if countToMigrate > 0 {
			if _, err := tx.ExecContext(ctx, `UPDATE tasks
                                SET progress_history = jsonb_build_object(
                                    'entry_1', jsonb_build_object(
                                        'content', CONCAT('=== Progress 1 ===', E'\n', details),
                                        'timestamp', COALESCE(updated_at::text, created_at::text),
                                        'progress_number', 1
                                    )
                                ),
                                progress_count = 1
                                WHERE details IS NOT NULL
                                AND (progress_history IS NULL OR progress_history::text = '{}');`); err != nil {
				_ = tx.Rollback()
				return false
			}
		}
		if _, err := tx.ExecContext(ctx, `ALTER TABLE tasks DROP COLUMN details;`); err != nil {
			_ = tx.Rollback()
			return false
		}
	}
	if _, err := tx.ExecContext(ctx, `CREATE INDEX IF NOT EXISTS idx_tasks_progress_count
                        ON tasks(progress_count);`); err != nil {
		_ = tx.Rollback()
		return false
	}
	if err := tx.Commit(); err != nil {
		return false
	}
	return true
}

// InitializeDatabase creates the uuid-ossp extension.
func (m *DatabaseMigrator) InitializeDatabase() bool {
	if !strings.Contains(m.DatabaseURL, "postgresql") {
		return true
	}
	db, err := database.PgxOpener(m.DatabaseURL, database.EngineOptions{})
	if err != nil {
		return false
	}
	defer db.Close()
	if _, err := db.ExecContext(context.Background(), `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`); err != nil {
		return false
	}
	return true
}

// EnsureDatabaseReady initializes then migrates; always true like Python.
func (m *DatabaseMigrator) EnsureDatabaseReady() bool {
	m.InitializeDatabase()
	m.RunMigrations()
	return true
}

var (
	migratorMu       sync.Mutex
	migratorInstance *DatabaseMigrator
)

// GetMigrator returns the singleton migrator.
func GetMigrator(databaseURL string) *DatabaseMigrator {
	migratorMu.Lock()
	defer migratorMu.Unlock()
	if migratorInstance == nil {
		migratorInstance = NewDatabaseMigrator(databaseURL)
	}
	return migratorInstance
}

// RunStartupMigrations runs migrations, automatic migrations and the current-user
// initialization. Migration failures are reported only through the returned success flag.
func RunStartupMigrations(databaseURL string) bool {
	migrator := GetMigrator(databaseURL)
	success := migrator.EnsureDatabaseReady()
	if success {
		deps := database.OSDeps()
		ctx := context.Background()
		if db, err := deps.Open(migrator.DatabaseURL, database.EngineOptions{}); err == nil {
			database.RunAutoMigrations(ctx, db)
			_ = db.Close()
		}
		InitializeDatabaseForCurrentUser()
	}
	return success
}
