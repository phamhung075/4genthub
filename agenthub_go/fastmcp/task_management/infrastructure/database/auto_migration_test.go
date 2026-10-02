package database_test

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestAutoMigrationRealPostgres(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true")
	dsn := newTestDatabase(t)
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
	if !database.RunAutoMigrations(ctx, db) {
		t.Fatal("RunAutoMigrations returned false")
	}
	for _, table := range []string{"tasks", "subtasks"} {
		var exists bool
		if err := db.QueryRowContext(ctx, `SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = $1 AND column_name = 'progress_state')`, table).Scan(&exists); err != nil {
			t.Fatal(err)
		}
		if !exists {
			t.Fatalf("%s.progress_state missing", table)
		}
	}
}
