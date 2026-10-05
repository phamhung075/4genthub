// Package testdb gives tests a real, empty Postgres database with the application schema.
package testdb

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
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
		t.Skip("AGENTHUB_TEST_PG_URL not set")
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
	if err := cfg.CreateTables(context.Background()); err != nil {
		t.Fatal(err)
	}
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
