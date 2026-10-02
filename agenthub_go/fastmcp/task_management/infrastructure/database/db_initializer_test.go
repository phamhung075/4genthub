package database_test

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestDBInitializerRealPostgres(t *testing.T) {
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
	inst, err := database.NewDatabaseInitializer(ctx, database.OSDeps(), cfg)
	if err != nil {
		t.Fatal(err)
	}
	if !inst.Initialize() {
		t.Fatal("Initialize returned false")
	}
	if !inst.Initialized {
		t.Fatal("Initialized flag not set")
	}
	if !inst.VerifyTableStructure() {
		t.Fatal("VerifyTableStructure failed")
	}
	if !inst.RequiredTables()["projects"] {
		t.Fatal("RequiredTables missing projects")
	}
	if !inst.CheckAndInit() {
		t.Fatal("CheckAndInit returned false")
	}
}
