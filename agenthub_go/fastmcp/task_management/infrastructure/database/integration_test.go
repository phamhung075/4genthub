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

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// NewTestDatabase creates an empty database and returns a DSN for it plus a cleanup.
func newTestDatabase(t *testing.T) string {
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
	testdb.CreateSchema(t, cfg)
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
	// THE STEPS ARE THE CREATOR, so the assertion is that every table the registry declares exists -
	// not that the count equals the registry's, which was only ever true while createAll did the work:
	// 0001 is a static snapshot and carries tables whose init() registration is absent from this test
	// binary's imports.
	created := map[string]bool{}
	for _, n := range names {
		created[n] = true
	}
	for _, def := range database.Tables {
		if !created[def.Name] {
			t.Errorf("the steps did not create the registered table %q", def.Name)
		}
	}
	if !created["applied_migrations"] {
		t.Fatalf("the migration ledger is absent after CreateTables: %s", strings.Join(names, ","))
	}
	var ledger bool
	if err := db.QueryRowContext(ctx, `SELECT to_regclass('applied_migrations') IS NOT NULL`).Scan(&ledger); err != nil || !ledger {
		t.Fatalf("the migration ledger is absent after CreateTables: %v", err)
	}
	var labels string
	if err := db.QueryRowContext(ctx, "SELECT string_agg(enumlabel, ',' ORDER BY enumsortorder) FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='progressstate'").Scan(&labels); err != nil || labels != "INITIAL,IN_PROGRESS,COMPLETE" {
		t.Fatalf("enum labels %q %v", labels, err)
	}
	// The ai_* columns are the schema's own now (0001, or 0005 on a database that predates them),
	// so the readback is the assertion: there is no separate creator left to run.
	status := database.VerifyAIColumns(ctx, db)
	entry, ok := status.Get("tasks")
	if !ok {
		t.Fatalf("verify: %v", status.Keys())
	}
	if count, _ := entry.(*entities.OrderedMap[any]).Get("ai_columns_count"); count != 7 {
		t.Fatalf("tasks carries %v ai_* columns, want 7: %v", count, status.Keys())
	}
}
