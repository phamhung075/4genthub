package fastmcp_test

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp"
	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newFastmcpTestDatabase creates a throwaway database on the cluster AGENTHUB_TEST_PG_URL names,
// brings the schema up in it, and returns the database's DSN - which is what the initializer under
// test is constructed from, so the case reads the database through the URL production would use.
//
// The bring-up is testdb.CreateSchema, not a bare cfg.CreateTables: the gated carry step
// 0003_progress_history_carry_and_drop refuses on a database whose ledger holds no 0001_baseline
// row, and createAll populates the catalogue before the runner runs, so a fresh fixture database
// skips the frozen baseline without recording it and the bare boot refuses with P0001.
// CreateSchema performs the operator's mark and boots again.
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
	dsn := u.String()
	pool, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2})
	if err != nil {
		t.Fatal(err)
	}
	// The pool outlives this helper, so it is closed by a cleanup rather than a defer. Cleanups run
	// last registered first, so this one closes the pool BEFORE the drop-registered-above runs.
	t.Cleanup(func() { pool.Close() })
	testdb.CreateSchema(t, &database.DatabaseConfig{Engine: &database.Engine{DB: pool, URL: dsn}})
	return dsn
}

func TestDatabaseInitializerCreateDefaultProject(t *testing.T) {
	dsn := newFastmcpTestDatabase(t)
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
