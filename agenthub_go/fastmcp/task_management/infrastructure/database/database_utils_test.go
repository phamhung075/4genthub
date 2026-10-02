package database_test

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestDatabaseUtilsRealPostgres(t *testing.T) {
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
	utils := database.NewDatabaseUtils(ctx, cfg)
	health := utils.CheckDatabaseHealth()
	if status, _ := health.Get("status"); status != "healthy" {
		t.Fatalf("health = %v", health.Keys())
	}
	integrity, err := utils.ValidateSchemaIntegrity()
	if err != nil {
		t.Fatal(err)
	}
	if checked, _ := integrity.Get("tables_checked"); checked.(int) < 1 {
		t.Fatalf("tables_checked = %v", checked)
	}
	// Python's timestamp type check compares against "datetime", so PostgreSQL timestamp
	// columns are reported as errors (status invalid). That quirk is preserved.
	status, _ := integrity.Get("status")
	if status != "invalid" {
		t.Fatalf("status = %v (expected invalid, matching Python)", status)
	}
	indexes, err := utils.CreatePerformanceIndexes()
	if err != nil {
		t.Fatal(err)
	}
	if created, _ := indexes.Get("indexes_created"); len(created.([]any)) != 5 {
		t.Fatalf("indexes_created = %v", created)
	}
}

func TestDatabaseUtilsNormalizeTimestamp(t *testing.T) {
	utils := database.NewDatabaseUtils(context.Background(), &database.DatabaseConfig{})
	norm, err := utils.NormalizeTimestamp("2024-01-02T03:04:05Z")
	if err != nil || norm == nil {
		t.Fatalf("NormalizeTimestamp = %v, %v", norm, err)
	}
	if !norm.Equal(time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)) {
		t.Fatalf("normalized = %v", norm)
	}
	if got, err := utils.NormalizeTimestamp(nil); err != nil || got != nil {
		t.Fatalf("NormalizeTimestamp(nil) = %v, %v", got, err)
	}
	start := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	end := time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC)
	normStart, normEnd, err := utils.ValidateTimestampRange(&start, &end)
	if err != nil || !normStart.Before(normEnd) {
		t.Fatalf("ValidateTimestampRange = %v, %v, %v", normStart, normEnd, err)
	}
	if _, _, err := utils.ValidateTimestampRange(&end, &start); err == nil {
		t.Fatal("expected error for reversed range")
	}
}
