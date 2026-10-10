// Package fastmcp ports the top-level modules of the Python fastmcp package.
package fastmcp

// Database initialization - creates initial projects and branches if needed (Python
// fastmcp/database_init.py). The default connection URL is built exactly as in Python,
// including its development defaults.

import (
	"context"
	"crypto/rand"
	"database/sql"
	"fmt"
	"os"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// DatabaseInitializer handles initial database setup with default projects and branches.
type DatabaseInitializer struct {
	DatabaseURL string
}

// NewDatabaseInitializer builds the URL from the argument or the environment.
func NewDatabaseInitializer(databaseURL string) *DatabaseInitializer {
	if databaseURL != "" {
		return &DatabaseInitializer{DatabaseURL: databaseURL}
	}
	return &DatabaseInitializer{DatabaseURL: buildDatabaseURLFromEnv()}
}

// buildDatabaseURLFromEnv mirrors the Python URL construction shared by database_init and
// database_migrations.
func buildDatabaseURLFromEnv() string {
	dbType := os.Getenv("DATABASE_TYPE")
	if dbType == "" {
		dbType = "postgresql"
	}
	if dbType == "postgresql" {
		host := envOr("DATABASE_HOST", "localhost")
		port := envOr("DATABASE_PORT", "5432")
		name := envOr("DATABASE_NAME", "postgresdb")
		user := envOr("DATABASE_USER", "agenthub_user")
		password := envOr("DATABASE_PASSWORD", "agenthub_password")
		return fmt.Sprintf("postgresql://%s:%s@%s:%s/%s", user, password, host, port, name)
	}
	return envOr("DATABASE_URL", "sqlite:///agenthub_dev.db")
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// CreateDefaultProject creates a default project and branch for a user if they have none;
// the bool reports whether the row was found or created (Python returns None on error).
func (d *DatabaseInitializer) CreateDefaultProject(userID string) (string, bool) {
	db, err := database.PgxOpener(d.DatabaseURL, database.EngineOptions{})
	if err != nil {
		return "", false
	}
	defer db.Close()
	ctx := context.Background()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return "", false
	}
	var existing string
	err = tx.QueryRowContext(ctx, `SELECT id FROM projects WHERE user_id = $1 LIMIT 1;`, userID).Scan(&existing)
	if err == nil {
		_ = tx.Commit()
		return existing, true
	}
	if err != sql.ErrNoRows {
		_ = tx.Rollback()
		return "", false
	}
	projectID := databaseInitUUID4()
	now := time.Now().UTC()
	if _, err := tx.ExecContext(ctx, `INSERT INTO projects (id, name, description, user_id, status, metadata, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8);`,
		projectID, "My First Project", "Welcome to agenthub! This is your default project.",
		userID, "active", "{}", now, now); err != nil {
		_ = tx.Rollback()
		return "", false
	}
	branchID := databaseInitUUID4()
	if _, err := tx.ExecContext(ctx, `INSERT INTO project_git_branchs (
                            id, project_id, name, description, user_id,
                            priority, status, metadata, task_count, completed_task_count,
                            created_at, updated_at
                        )
                        VALUES (
                            $1, $2, $3, $4, $5,
                            $6, $7, $8, $9, $10,
                            $11, $12
                        );`,
		branchID, projectID, "main", "Main development branch", userID,
		"medium", "active", "{}", 0, 0, now, now); err != nil {
		_ = tx.Rollback()
		return "", false
	}
	if err := tx.Commit(); err != nil {
		return "", false
	}
	return projectID, true
}

// EnsureTablesExist checks the four core tables exist.
func (d *DatabaseInitializer) EnsureTablesExist() bool {
	db, err := database.PgxOpener(d.DatabaseURL, database.EngineOptions{})
	if err != nil {
		return false
	}
	defer db.Close()
	var tableCount int
	err = db.QueryRowContext(context.Background(), `SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name IN ('projects', 'project_git_branchs', 'tasks', 'subtasks');`).Scan(&tableCount)
	if err != nil {
		return false
	}
	return tableCount >= 4
}

func databaseInitUUID4() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return ""
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
