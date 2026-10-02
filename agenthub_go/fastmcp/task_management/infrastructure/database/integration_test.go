package database_test

// Integration tests against a real PostgreSQL. They run only when AGENTHUB_TEST_PG_URL points
// at an administrative database (for example postgresql://agenthub_user@127.0.0.1:55432/postgres):
// each test creates and drops its own database.

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// NewTestDatabase creates an empty database and returns a DSN for it plus a cleanup.
func newTestDatabase(t *testing.T) string {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	db, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	name := fmt.Sprintf("agenthub_test_%d", time.Now().UnixNano())
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

func TestRealPostgresCreateTablesAndSessions(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true")
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()

	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	// idempotent (checkfirst)
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	rows, err := db.QueryContext(ctx, "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1")
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for rows.Next() {
		var n string
		_ = rows.Scan(&n)
		names = append(names, n)
	}
	rows.Close()
	if len(names) != len(database.Tables) {
		t.Fatalf("created %d tables, want %d: %s", len(names), len(database.Tables), strings.Join(names, ","))
	}
	var labels string
	if err := db.QueryRowContext(ctx, "SELECT string_agg(enumlabel, ',' ORDER BY enumsortorder) FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='progressstate'").Scan(&labels); err != nil || labels != "INITIAL,IN_PROGRESS,COMPLETE" {
		t.Fatalf("enum labels %q %v", labels, err)
	}
	if !database.EnsureAIColumnsExist(ctx, db) {
		t.Fatal("EnsureAIColumnsExist failed on a real database")
	}
	status := database.VerifyAIColumns(ctx, db)
	if _, ok := status.Get("tasks"); !ok {
		t.Fatalf("verify: %v", status.Keys())
	}
}
