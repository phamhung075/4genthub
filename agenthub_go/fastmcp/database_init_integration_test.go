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
