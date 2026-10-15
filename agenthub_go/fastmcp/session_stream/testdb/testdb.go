// Package testdb gives tests a real, empty Postgres database with the application schema.
package testdb

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

// NewSessions creates an empty database on the Postgres named by AGENTHUB_TEST_PG_URL
// (an admin URL such as postgres://postgres@127.0.0.1:54329/postgres?sslmode=disable),
// creates the schema in it and drops it when the test ends; without the variable the
// test skips. A throwaway server needs no install: with the binaries in
// ~/.cache/agenthub-testpg/bin (PostgreSQL 16.4),
//
//	initdb -D $DIR -U postgres --auth=trust -E UTF8 --locale=C
//	printf "listen_addresses='127.0.0.1'\nport=54329\nunix_socket_directories=''\nfsync=off\n" >> $DIR/postgresql.conf
//	pg_ctl -D $DIR -l $DIR/pg.log -w start
//	cd agenthub_go && AGENTHUB_TEST_PG_URL='postgres://postgres@127.0.0.1:54329/postgres?sslmode=disable' \
//	  go test -count=1 ./fastmcp/session_stream/ ./fastmcp/server/httpapp/
//
// and `pg_ctl -D $DIR stop` afterwards.
func NewSessions(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("SKIPPED, NOT PASSED: AGENTHUB_TEST_PG_URL is unset, so this case did NOT run - " +
			"bash tools/testpg/start.sh prints a URL to pass to it")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_stream_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	adm.Close()
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "x", "DATABASE_PASSWORD": "x"}
	database.ResetInstance()
	deps := database.Deps{
		Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
		Sleep:  func(time.Duration) {},
		Open: func(string, database.EngineOptions) (*sql.DB, error) {
			return database.PgxOpener(u.String(), database.EngineOptions{PoolSize: 4, MaxOverflow: 4, PoolRecycle: 60})
		},
	}
	cfg, err := database.GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	CreateSchema(t, cfg)
	database.SetupTimestampEvents()
	t.Cleanup(func() {
		database.ResetInstance()
		adm, err := sql.Open("pgx", admin)
		if err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	return database.NewSessionManager(cfg)
}

// CreateSchema creates the application schema in the database cfg points at, performing the boot the
// merged runner now requires.
//
// THE FIRST BOOT IS EXPECTED TO REFUSE, AND THAT IS THE RUNNER'S BEHAVIOUR, NOT A BROKEN FIXTURE:
// createAll populates the catalogue BEFORE the runner runs, so the runner skips the frozen 0001
// baseline WITHOUT recording it, and the gated carry step (0003_progress_history_carry_and_drop)
// then refuses on a database whose ledger holds no 0001_baseline row. Recording that mark is the
// OWNER's action, so this helper records it the way an operator does - Runner.MarkBaseline - and
// boots again. The refusal is asserted rather than swallowed, so a runner that let the destructive
// step through would fail every case that uses this helper instead of quietly handing them a
// carried database.
func CreateSchema(t *testing.T, cfg *database.DatabaseConfig) {
	t.Helper()
	ctx := context.Background()
	err := cfg.CreateTables(ctx)
	if err == nil {
		t.Fatal("the boot built the schema without refusing: the gated carry step ran with no 0001_baseline row")
	}
	if !strings.Contains(err.Error(), "0001_baseline") {
		t.Fatalf("the first boot refused, but not for the missing baseline mark: %v", err)
	}
	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := (&database.Runner{Sessions: database.NewSessionManager(cfg), Set: set}).
		MarkBaseline(ctx, "0001_baseline"); err != nil {
		t.Fatalf("recording the owner's baseline mark failed: %v", err)
	}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("the boot after the owner's mark failed: %v", err)
	}
}
