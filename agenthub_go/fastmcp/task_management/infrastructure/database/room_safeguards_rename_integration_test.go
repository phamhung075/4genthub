package database_test

// The 0008 step against a real PostgreSQL, on the database it exists for: one that holds the
// safeguard table and the decision column under the retired names. A fresh database takes the room
// names from `0001_baseline` and skips `0001` here, because the runner skips a baseline whenever the
// catalogue is already populated - so this fixture builds the pre-rename shape by hand, the way the
// 0004 case does, and the step has to carry it.
//
// What it proves: the table, its column, its three CHECKs, its primary key and its connector index all
// say room afterwards; the decision column says room_name; the rows are carried rather than rewritten;
// a second application is a no-op; and a database with neither table is untouched instead of failing
// the boot with SQLSTATE 42P01.

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

const roomNamesStep = "0008_the_safeguard_and_decision_names_say_room"

// legacySafeguardAndDecisionTables is the shape 0001 created before the rename: the table, its column,
// its constraints, its index and the decision column the room's name lived in.
const legacySafeguardAndDecisionTables = `
CREATE TABLE rig_safeguards (
	user_id VARCHAR(64) NOT NULL,
	connector_id VARCHAR(64) NOT NULL,
	rig VARCHAR(255) NOT NULL,
	safeguard VARCHAR(32) NOT NULL,
	state VARCHAR(20) NOT NULL,
	pid INTEGER,
	restarts INTEGER NOT NULL,
	age_s INTEGER NOT NULL,
	last_beat_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (user_id, connector_id, rig, safeguard),
	CONSTRAINT ck_rig_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
	CONSTRAINT ck_rig_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'messages', 'roomguard', 'bridge', 'agent')),
	CONSTRAINT ck_rig_safeguards_rig CHECK (CASE WHEN safeguard IN ('bridge', 'agent') THEN rig = '' ELSE length(rig) BETWEEN 1 AND 255 END)
);
CREATE INDEX ix_rig_safeguards_user_connector ON rig_safeguards (user_id, connector_id);
CREATE TABLE room_decisions (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	rig_name TEXT NOT NULL,
	acked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
);
CREATE INDEX ix_room_decisions_user_rig_state_acked ON room_decisions (user_id, rig_name, acked_at);
`

func TestTheRoomNamesStepRenamesTheSafeguardTableAndTheDecisionColumn(t *testing.T) {
	sessions, _ := newBareRunnerEnv(t)
	ctx := context.Background()
	exec := func(sql string) {
		t.Helper()
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, sql)
			return err
		}); err != nil {
			t.Fatalf("statement %q failed: %v", strings.SplitN(sql, "\n", 2)[0], err)
		}
	}
	scalar := func(query string) string {
		t.Helper()
		var got string
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			return s.QueryRowContext(ctx, query).Scan(&got)
		}); err != nil {
			t.Fatal(err)
		}
		return got
	}

	exec(legacySafeguardAndDecisionTables)
	exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s)
	      VALUES ('u1', 'c1', 'room-1', 'compact', 'running', 7, 9)`)
	exec(`INSERT INTO room_decisions (id, user_id, rig_name) VALUES ('5b0f2a86-8f19-4c34-9f4b-0f2b1f2f6a01', 'u1', 'room-1')`)

	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{embeddedStep(t, roomNamesStep)}}
	applied, err := runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the step failed: %v", err)
	}
	if len(applied) != 1 || applied[0] != roomNamesStep {
		t.Fatalf("the run applied %v, want just %s", applied, roomNamesStep)
	}

	// The table and the column, and the absence of the names they carried.
	if got := scalar(`SELECT coalesce(to_regclass('rig_safeguards')::text, '')`); got != "" {
		t.Errorf("rig_safeguards still resolves as %q, want nothing: the rename is not an alias", got)
	}
	if got := scalar(`SELECT to_regclass('room_safeguards')::text`); got == "" {
		t.Error("room_safeguards does not resolve: the step did not rename the table")
	}
	if got := scalar(`SELECT string_agg(column_name, ',') FROM information_schema.columns
	                   WHERE table_schema = current_schema() AND table_name = 'room_safeguards'
	                     AND column_name IN ('rig', 'room')`); got != "room" {
		t.Errorf("the safeguard table carries %q where it wants exactly the room column", got)
	}
	if got := scalar(`SELECT room FROM room_safeguards WHERE user_id = 'u1'`); got != "room-1" {
		t.Errorf("the stored row reads %q, want the value it was written with: a rename carries rows", got)
	}

	// The three CHECKs follow the table token and the column suffix, and no `ck_rig_` name survives.
	if got := scalar(`SELECT string_agg(conname, ',' ORDER BY conname) FROM pg_constraint
	                   WHERE conrelid = 'room_safeguards'::regclass AND contype = 'c'`); got !=
		"ck_room_safeguards_room,ck_room_safeguards_safeguard,ck_room_safeguards_state" {
		t.Errorf("the table's CHECKs are %q, want the three ck_room_ names", got)
	}
	if got := scalar(`SELECT string_agg(conname, ',') FROM pg_constraint
	                   WHERE conrelid = 'room_safeguards'::regclass AND contype = 'p'`); got != "room_safeguards_pkey" {
		t.Errorf("the primary key is %q, want room_safeguards_pkey", got)
	}

	// The index, and the constraint it no longer names the old column in.
	if got := scalar(`SELECT string_agg(indexname, ',' ORDER BY indexname) FROM pg_indexes
	                   WHERE schemaname = current_schema() AND tablename = 'room_safeguards'`); got !=
		"ix_room_safeguards_user_connector,room_safeguards_pkey" {
		t.Errorf("the table's indexes are %q, want the pkey and the renamed connector index", got)
	}
	if got := scalar(`SELECT string_agg(column_name, ',') FROM information_schema.columns
	                   WHERE table_schema = current_schema() AND table_name = 'room_decisions'
	                     AND column_name IN ('rig_name', 'room_name')`); got != "room_name" {
		t.Errorf("room_decisions carries %q where it wants exactly room_name", got)
	}
	if got := scalar(`SELECT room_name FROM room_decisions WHERE user_id = 'u1'`); got != "room-1" {
		t.Errorf("the stored decision reads %q, want the value it was written with", got)
	}

	// IDEMPOTENCE: the ledger stops a second boot, so the SQL itself must survive a second application
	// for the case a ledger row is lost. Every branch is guarded on a name that no longer exists.
	exec(embeddedStep(t, roomNamesStep).SQL)
	if got := scalar(`SELECT room FROM room_safeguards WHERE user_id = 'u1'`); got != "room-1" {
		t.Errorf("a second application left the row reading %q, want room-1", got)
	}
	if applied, err := runner.Apply(ctx); err != nil || len(applied) != 0 {
		t.Errorf("the recorded step ran again: applied %v err %v", applied, err)
	}
}

// A database whose catalogue holds neither table is the ordinary state before the registry creates its
// tables, and an ALTER there is SQLSTATE 42P01, which takes the whole boot down. The step must find
// nothing to rename and leave no table behind either.
func TestTheRoomNamesStepIsANoOpWithoutItsTables(t *testing.T) {
	sessions, _ := newBareRunnerEnv(t)
	ctx := context.Background()

	var name string
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT coalesce(to_regclass('room_safeguards')::text, '')`).Scan(&name)
	}); err != nil {
		t.Fatal(err)
	}
	if name != "" {
		t.Fatalf("the fixture database already holds %q, so this case would prove nothing", name)
	}

	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{embeddedStep(t, roomNamesStep)}}
	if _, err := runner.Apply(ctx); err != nil {
		t.Fatalf("the step failed on a database without its tables: %v", err)
	}
	// Applying the SQL again bypasses the ledger, the same way the 0004 case proves its own guard.
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, embeddedStep(t, roomNamesStep).SQL)
		return err
	}); err != nil {
		t.Fatalf("the SQL failed on a database without its tables: %v", err)
	}
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT coalesce(to_regclass('room_safeguards')::text, '')`).Scan(&name)
	}); err != nil {
		t.Fatal(err)
	}
	if name != "" {
		t.Errorf("the step created %q, want nothing: it renames, it does not invent", name)
	}
}
