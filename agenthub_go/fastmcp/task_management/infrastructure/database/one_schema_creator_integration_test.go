package database_test

// ONE CREATOR, PINNED BY BEHAVIOUR. The schema used to have two authors - createAll (the TableDef
// registry) alongside the embedded steps - and a boot ran both. The seat-tier decision of 2026-10-17
// left the migrations, and the case here is the one a restored second author cannot pass: a
// catalogue that already holds tables is the state in which 0001 is SKIPPED, so a table the registry
// defines but no other step creates must STAY ABSENT after a boot. createAll would put it back; the
// steps do not. The other direction (a fresh database has every registry table) is
// TestRealPostgresCreateTablesAndSessions, so this pair says the registry's shape arrives exactly
// once, through the ledger.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestTheBootDoesNotRecreateAMissingTable is the guard against a second creator returning. `labels` is
// in the runtime registry and is created only by 0001_baseline; no later step touches it.
func TestTheBootDoesNotRecreateAMissingTable(t *testing.T) {
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	ctx := context.Background()

	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("the fresh boot failed: %v", err)
	}
	if _, err := db.ExecContext(ctx, `DROP TABLE IF EXISTS labels CASCADE`); err != nil {
		t.Fatalf("the table could not be dropped: %v", err)
	}

	// 0001 is skipped on a catalogue that already holds tables, and NO step creates `labels`, so a boot
	// that succeeds without it is the one creator's behaviour. A boot that recreates it is a second
	// author reading the registry behind the ledger's back.
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("the boot failed on a catalogue without labels: %v", err)
	}
	var present bool
	if err := db.QueryRowContext(ctx, `SELECT to_regclass('labels') IS NOT NULL`).Scan(&present); err != nil {
		t.Fatal(err)
	}
	if present {
		t.Fatal("the boot recreated a table only 0001_baseline defines: a creator other than the embedded steps is back")
	}
}
