package database

import (
	"context"
	"database/sql"
	"strings"
	"testing"
	"time"
)

func TestDatabaseConfigInitFlow(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "")
	ResetInstance()
	defer ResetInstance()
	f := newFakeDB()
	var opts EngineOptions
	var url string
	env := map[string]string{"DATABASE_TYPE": "PostgreSQL", "DATABASE_HOST": "h", "DATABASE_PASSWORD": "p w", "DATABASE_POOL_SIZE": "7"}
	deps := Deps{Getenv: envFrom(env), Sleep: func(time.Duration) {}, Open: func(u string, o EngineOptions) (*sql.DB, error) {
		url, opts = u, o
		return f.open(u, o)
	}}
	cfg, err := GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	if url != "postgresql://postgres:p%20w@h:5432/agenthub?sslmode=prefer" || opts.PoolSize != 7 || opts.MaxOverflow != 100 || !opts.PoolPrePing {
		t.Fatalf("url=%s opts=%+v", url, opts)
	}
	if cfg.DatabaseType != "postgresql" {
		t.Fatal(cfg.DatabaseType)
	}
	conn, err := cfg.GetSession(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	conn.Close()
	again, _ := GetInstance(context.Background(), deps)
	if again != cfg {
		t.Fatal("singleton expected")
	}
}

func TestDatabaseConfigErrors(t *testing.T) {
	ResetInstance()
	defer ResetInstance()
	for env, want := range map[string]string{
		"":                         "DATABASE_TYPE environment variable is NOT configured",
		"DATABASE_TYPE=mysql":      "Invalid DATABASE_TYPE: mysql",
		"DATABASE_TYPE=postgresql": "Database configuration missing for postgresql",
		"DATABASE_TYPE=postgresql,DATABASE_HOST=h,DATABASE_PASSWORD=p,DATABASE_POOL_SIZE=x": "invalid literal for int()",
	} {
		m := map[string]string{}
		for _, kv := range strings.Split(env, ",") {
			if p := strings.SplitN(kv, "=", 2); len(p) == 2 {
				m[p[0]] = p[1]
			}
		}
		_, err := newDatabaseConfig(context.Background(), Deps{Getenv: envFrom(m), Sleep: func(time.Duration) {}, Open: newFakeDB().open})
		if err == nil || !strings.Contains(err.Error(), want) {
			t.Errorf("%q: got %v want %q", env, err, want)
		}
	}
}
