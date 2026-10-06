package httpapp

// The IN-PROCESS IDEMPOTENCE half of the schema-upgrade gate (owner instruction after packet 4:
// "add the upgrade test to your gate list for any packet that changes schema"). The other half is
// the two-binary procedure, which the writer owns as a required step; this half is the part a
// script cannot see, because it re-runs the migration path INSIDE one process the way a restart
// does not.
//
// WHY IT EXISTS: the closing boot that a packet used to get runs the NEW binary against a FRESH
// database with AUTO_MIGRATE=false. That proves the binary runs and proves NOTHING about
// migrations - while production runs AUTO_MIGRATE=true against an EXISTING database. The manual
// upgrade procedure (old binary, then new binary, then new binary again) covers that; the third
// step is what this test makes permanent and automatic.
//
// IT REUSES THE BRING-UP THIS PACKAGE ALREADY HAS rather than opening its own database: a test that
// boots its own way proves nothing about the way production boots. That bring-up skips loudly
// without AGENTHUB_TEST_PG_URL, so this test does too.

import (
	"context"
	"database/sql"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// schemaFingerprint is every column, index and constraint of the public schema as sorted strings.
// Comparing it across two migration runs is what "idempotent" means here: the SAME objects, not
// merely "no error returned".
func schemaFingerprint(t *testing.T, db *sql.DB) []string {
	t.Helper()
	ctx := context.Background()
	out := []string{}

	columns, err := db.QueryContext(ctx, `SELECT table_name || '.' || column_name || ':' || data_type || ':' || is_nullable
		FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1`)
	if err != nil {
		t.Fatalf("read columns: %v", err)
	}
	defer columns.Close()
	for columns.Next() {
		var item string
		if err := columns.Scan(&item); err != nil {
			t.Fatalf("scan column: %v", err)
		}
		out = append(out, "column "+item)
	}
	if err := columns.Err(); err != nil {
		t.Fatalf("columns: %v", err)
	}

	indexes, err := db.QueryContext(ctx, `SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY 1`)
	if err != nil {
		t.Fatalf("read indexes: %v", err)
	}
	defer indexes.Close()
	for indexes.Next() {
		var item string
		if err := indexes.Scan(&item); err != nil {
			t.Fatalf("scan index: %v", err)
		}
		out = append(out, "index "+item)
	}
	if err := indexes.Err(); err != nil {
		t.Fatalf("indexes: %v", err)
	}

	constraints, err := db.QueryContext(ctx, `SELECT c.conname || ':' || c.contype::text FROM pg_constraint c
		JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'public' ORDER BY 1`)
	if err != nil {
		t.Fatalf("read constraints: %v", err)
	}
	defer constraints.Close()
	for constraints.Next() {
		var item string
		if err := constraints.Scan(&item); err != nil {
			t.Fatalf("scan constraint: %v", err)
		}
		out = append(out, "constraint "+item)
	}
	if err := constraints.Err(); err != nil {
		t.Fatalf("constraints: %v", err)
	}

	sort.Strings(out)
	return out
}

func TestSchemaMigrationIsIdempotentInProcess(t *testing.T) {
	// The bring-up this package already has: a throwaway database, created and migrated ONCE.
	newMissedNotificationAppEnv(t)

	ctx := context.Background()
	cfg, err := database.GetInstance(ctx, database.OSDeps())
	if err != nil {
		t.Fatalf("GetInstance: %v", err)
	}
	if cfg == nil || cfg.Engine == nil || cfg.Engine.DB == nil {
		t.Fatal("no database handle: the bring-up did not leave an initialised config")
	}

	before := schemaFingerprint(t, cfg.Engine.DB)

	// The objects the upgrade must have produced by this point - the same ones the manual
	// two-binary procedure checks by hand after step 2.
	for _, want := range []struct{ kind, name string }{
		{"column", "seat_feedback."},
		{"column", "rooms.team_id:"},
		{"index", "ix_rooms_team_id"},
		{"constraint", "rooms_team_id_fkey:"},
		{"constraint", "ck_seat_feedback_layer:"},
	} {
		found := false
		for _, item := range before {
			if strings.HasPrefix(item, want.kind+" "+want.name) {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("%s %q is missing from the migrated schema", want.kind, want.name)
		}
	}

	// The same migration path a SECOND time, in this process: tables, the AI columns and the
	// registered column ensurers all run again, exactly as a restart against an existing database
	// would run them.
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatalf("second CreateTables run: %v (a re-run against an existing schema must be a no-op)", err)
	}

	after := schemaFingerprint(t, cfg.Engine.DB)
	if len(before) != len(after) {
		t.Fatalf("the schema changed on a second run: %d objects before, %d after", len(before), len(after))
	}
	for i := range before {
		if before[i] != after[i] {
			t.Fatalf("the schema changed on a second run:\n before: %s\n after:  %s", before[i], after[i])
		}
	}
}
