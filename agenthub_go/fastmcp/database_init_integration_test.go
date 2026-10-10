package fastmcp_test

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func newFastmcpTestDatabase(t *testing.T) string {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("SKIPPED, NOT PASSED: AGENTHUB_TEST_PG_URL is unset, so this case did NOT run - " +
			"bash tools/testpg/start.sh prints a URL to pass to it")
	}
	db, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	name := fmt.Sprintf("agenthub_init_test_%d", time.Now().UnixNano())
	if _, err := db.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		adm, err := sql.Open("pgx", admin)
		if err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	return u.String()
}

func TestDatabaseInitializerCreateDefaultProject(t *testing.T) {
	dsn := newFastmcpTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	init := fastmcp.NewDatabaseInitializer(dsn)
	if !init.EnsureTablesExist() {
		t.Fatal("EnsureTablesExist returned false")
	}
	projectID, ok := init.CreateDefaultProject("user-1")
	if !ok || projectID == "" {
		t.Fatalf("CreateDefaultProject = %q, %v", projectID, ok)
	}
	again, ok := init.CreateDefaultProject("user-1")
	if !ok || again != projectID {
		t.Fatalf("second CreateDefaultProject = %q, %v (want %q)", again, ok, projectID)
	}
}

func TestDatabaseMigratorRunMigrations(t *testing.T) {
	dsn := newFastmcpTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, `CREATE TABLE tasks (
		id VARCHAR PRIMARY KEY,
		status VARCHAR,
		details TEXT,
		created_at TIMESTAMP WITHOUT TIME ZONE,
		updated_at TIMESTAMP WITHOUT TIME ZONE
	)`); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `INSERT INTO tasks (id, status, details, created_at, updated_at) VALUES ('t1', 'todo', 'hello', now(), now())`); err != nil {
		t.Fatal(err)
	}
	migrator := fastmcp.NewDatabaseMigrator(dsn)
	if !migrator.RunMigrations() {
		t.Fatal("RunMigrations returned false")
	}
	var hasDetails, hasProgress bool
	if err := db.QueryRowContext(ctx, `SELECT
		EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'tasks' AND column_name = 'details'),
		EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'tasks' AND column_name = 'progress_history')`).Scan(&hasDetails, &hasProgress); err != nil {
		t.Fatal(err)
	}
	if hasDetails || !hasProgress {
		t.Fatalf("details=%v progress_history=%v", hasDetails, hasProgress)
	}
	var content string
	if err := db.QueryRowContext(ctx, `SELECT progress_history->'entry_1'->>'content' FROM tasks WHERE id = 't1'`).Scan(&content); err != nil {
		t.Fatal(err)
	}
	if content != "=== Progress 1 ===\nhello" {
		t.Fatalf("content = %q", content)
	}
}
