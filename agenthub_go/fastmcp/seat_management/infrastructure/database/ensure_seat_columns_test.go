package database

// TestEnsureSeatColumnsExistOnOldSchema proves the migration path for an EXISTING database: a
// rooms table created before the D5 wiring (no team_id) gains the column, the nullability and the
// foreign key the fresh-schema path creates, and a room_decisions table created before the answer
// leg (no acked_at) gains the delivery marker and its COMPOSITE index - then a second run changes
// nothing.
//
// It creates its own throwaway database from SEAT_TEST_DATABASE_URL, because the premise is a
// table WITHOUT the column and the shared test database may already have it.

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"
)

func TestEnsureSeatColumnsExistOnOldSchema(t *testing.T) {
	admin := os.Getenv("SEAT_TEST_DATABASE_URL")
	if admin == "" {
		t.Skip("SKIPPED, NOT PASSED: SEAT_TEST_DATABASE_URL is unset, so this case did NOT run - " +
			"it applies the seat schema to a PostgreSQL it is given; bash tools/testpg/start.sh prints a URL")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	defer adm.Close()
	name := fmt.Sprintf("agenthub_seatcols_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	defer func() { _, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)") }()

	u, err := url.Parse(admin)
	if err != nil {
		t.Fatal(err)
	}
	u.Path = "/" + name
	db, err := sql.Open("pgx", u.String())
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()

	// The pre-wiring shape: teams exists (slice 1), rooms does not have team_id. NO SERVER DEFAULT
	// on id, matching what the runtime path creates — the schema file declares none either.
	if _, err := db.ExecContext(ctx, `CREATE TABLE teams (
		id UUID PRIMARY KEY,
		user_id TEXT NOT NULL,
		slug TEXT NOT NULL,
		name TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
		updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
	)`); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `CREATE TABLE rooms (
		id UUID PRIMARY KEY,
		user_id TEXT NOT NULL,
		slug TEXT NOT NULL,
		name TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
		updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
	)`); err != nil {
		t.Fatal(err)
	}
	// The pre-answer-leg shape of the decisions table: the S1 columns, no delivery marker.
	if _, err := db.ExecContext(ctx, `CREATE TABLE room_decisions (
		id UUID PRIMARY KEY,
		user_id TEXT NOT NULL,
		room_id UUID NOT NULL REFERENCES rooms (id),
		rig_name TEXT NOT NULL,
		qitem_id TEXT NOT NULL,
		author_seat_key TEXT NOT NULL,
		destination TEXT NOT NULL,
		summary TEXT,
		detail TEXT,
		questions JSONB NOT NULL,
		answers JSONB NOT NULL DEFAULT '{}'::jsonb,
		state TEXT NOT NULL,
		idempotency_key TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
		answered_at TIMESTAMP WITH TIME ZONE,
		resolved_at TIMESTAMP WITH TIME ZONE
	)`); err != nil {
		t.Fatal(err)
	}

	if err := EnsureSeatColumnsExist(ctx, db); err != nil {
		t.Fatalf("EnsureSeatColumnsExist: %v", err)
	}
	// Idempotent: the second run must be a no-op rather than an error.
	if err := EnsureSeatColumnsExist(ctx, db); err != nil {
		t.Fatalf("EnsureSeatColumnsExist (second run): %v", err)
	}

	var (
		dataType   string
		isNullable string
	)
	if err := db.QueryRowContext(ctx, `SELECT data_type, is_nullable FROM information_schema.columns
		WHERE table_name = 'rooms' AND column_name = 'team_id'`).Scan(&dataType, &isNullable); err != nil {
		t.Fatalf("team_id column: %v", err)
	}
	if dataType != "uuid" || isNullable != "YES" {
		t.Fatalf("team_id = %s null=%s, want uuid and nullable", dataType, isNullable)
	}

	// The constraint is the part a rollback trips on, so it is asserted, not assumed: the column
	// must reference teams, and a value that references nothing must be refused.
	var target string
	if err := db.QueryRowContext(ctx, `SELECT ccu.table_name FROM information_schema.table_constraints tc
		JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
		WHERE tc.table_name = 'rooms' AND tc.constraint_type = 'FOREIGN KEY'`).Scan(&target); err != nil {
		t.Fatalf("rooms has no foreign key to teams: %v", err)
	}
	if target != "teams" {
		t.Fatalf("rooms foreign key targets %q, want teams", target)
	}
	if _, err := db.ExecContext(ctx, `INSERT INTO rooms (id, user_id, slug, name, team_id)
		VALUES (uuid_generate_v4(), 'someone', 'dev', 'Dev', '00000000-0000-0000-0000-000000000000')`); err == nil {
		t.Fatal("a room accepted a team_id that references no team")
	}

	// The index is created with the column, so a lookup by team is not a sequential scan.
	var indexes int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM pg_indexes
		WHERE tablename = 'rooms' AND indexname = 'ix_rooms_team_id'`).Scan(&indexes); err != nil {
		t.Fatal(err)
	}
	if indexes != 1 {
		t.Fatalf("ix_rooms_team_id count = %d, want 1", indexes)
	}

	// The same two claims for the answer leg's delivery marker, and the index one is the sharper of
	// them: the column alone would satisfy the pull's WHERE, but the index has to be the COMPOSITE one
	// the fresh schema creates, so an index over acked_at by itself is a different object wearing the
	// same name - which is what the entry's own column list is for.
	var ackedType, ackedNullable string
	if err := db.QueryRowContext(ctx, `SELECT data_type, is_nullable FROM information_schema.columns
		WHERE table_name = 'room_decisions' AND column_name = 'acked_at'`).Scan(&ackedType, &ackedNullable); err != nil {
		t.Fatalf("acked_at column: %v", err)
	}
	if ackedType != "timestamp with time zone" || ackedNullable != "YES" {
		t.Fatalf("acked_at = %s null=%s, want timestamp with time zone and nullable", ackedType, ackedNullable)
	}
	var indexDef string
	if err := db.QueryRowContext(ctx, `SELECT indexdef FROM pg_indexes
		WHERE tablename = 'room_decisions' AND indexname = 'ix_room_decisions_user_rig_state_acked'`).Scan(&indexDef); err != nil {
		t.Fatalf("the delivery index: %v", err)
	}
	for _, col := range []string{"user_id", "rig_name", "state", "acked_at"} {
		if !strings.Contains(indexDef, col) {
			t.Errorf("indexdef = %s, want the composite index to cover %s", indexDef, col)
		}
	}
}
