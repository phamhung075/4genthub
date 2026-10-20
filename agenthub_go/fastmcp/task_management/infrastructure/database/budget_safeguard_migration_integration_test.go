package database_test

// The 0009 step against a real PostgreSQL, on the database it exists for: one whose room_safeguards
// CHECK still holds the six names, which is every database that ran 0004/0008 (0008 renames and does
// not restate the value list). The fixture therefore builds that table by hand in its post-0008 shape
// instead of booting the current schema, whose CHECK already names the seven.
//
// What it proves, in the order the task's acceptance states it: the step applies; a room-scoped
// `budget` row reaches the table afterwards; an unknown seventh name is still refused by the widened
// CHECK; the scope rule is untouched (`budget` with an empty room is refused); the rows already stored
// are carried, because widening a CHECK is no data move; applying the SQL a second time is a no-op;
// and a database without the table is left without one.

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgconn"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// budgetSafeguardStep is the step's name, which is also its identity in applied_migrations.
const budgetSafeguardStep = "0009_room_safeguards_accept_budget"

// sixNameRoomSafeguardsTable is the table as 0008 left it: the room names, the six-value CHECK this
// step widens, and the two constraints the step must leave alone.
const sixNameRoomSafeguardsTable = `CREATE TABLE room_safeguards (
	user_id VARCHAR(64) NOT NULL,
	connector_id VARCHAR(64) NOT NULL,
	room VARCHAR(255) NOT NULL,
	safeguard VARCHAR(32) NOT NULL,
	state VARCHAR(20) NOT NULL,
	pid INTEGER,
	restarts INTEGER NOT NULL,
	age_s INTEGER NOT NULL,
	last_beat_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (user_id, connector_id, room, safeguard),
	CONSTRAINT ck_room_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
	CONSTRAINT ck_room_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'messages', 'roomguard', 'bridge', 'agent')),
	CONSTRAINT ck_room_safeguards_room CHECK (CASE WHEN safeguard IN ('bridge', 'agent') THEN room = '' ELSE length(room) BETWEEN 1 AND 255 END)
)`

func TestTheBudgetStepWidensTheSixNameCheck(t *testing.T) {
	sessions, _ := newBareRunnerEnv(t)
	ctx := context.Background()
	exec := func(sql string) error {
		t.Helper()
		return sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, sql)
			return err
		})
	}
	mustExec := func(sql string) {
		t.Helper()
		if err := exec(sql); err != nil {
			t.Fatalf("statement %q failed: %v", strings.SplitN(sql, "\n", 2)[0], err)
		}
	}
	rows := func() int {
		t.Helper()
		count := 0
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			return s.QueryRowContext(ctx, `SELECT count(*) FROM room_safeguards`).Scan(&count)
		}); err != nil {
			t.Fatal(err)
		}
		return count
	}
	insert := func(room, safeguard string) error {
		t.Helper()
		return exec(`INSERT INTO room_safeguards (user_id, connector_id, room, safeguard, state, restarts, age_s)
		             VALUES ('u1', 'c1', '` + room + `', '` + safeguard + `', 'running', 0, 4)`)
	}
	wantCheckViolation := func(err error, constraint string) {
		t.Helper()
		var pgErr *pgconn.PgError
		if !errors.As(err, &pgErr) || pgErr.Code != "23514" || pgErr.ConstraintName != constraint {
			t.Fatalf("err = %v, want a 23514 check violation on %s", err, constraint)
		}
	}

	mustExec(sixNameRoomSafeguardsTable)
	// A row of each shape the six-value CHECK already admits: widening must carry both.
	mustExec(`INSERT INTO room_safeguards (user_id, connector_id, room, safeguard, state, restarts, age_s)
	          VALUES ('u1', 'c1', 'room-1', 'roomguard', 'running', 0, 4)`)
	mustExec(`INSERT INTO room_safeguards (user_id, connector_id, room, safeguard, state, restarts, age_s)
	          VALUES ('u1', 'c1', '', 'bridge', 'silent', 2, 9)`)

	// The name the widened constraint must refuse, proven BEFORE the step so the case is the step's.
	if err := insert("room-1", "budget"); err == nil {
		t.Fatal("the fixture's six-name CHECK admitted budget, so this case would prove nothing")
	}

	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{embeddedStep(t, budgetSafeguardStep)}}
	applied, err := runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the step failed: %v", err)
	}
	if len(applied) != 1 || applied[0] != budgetSafeguardStep {
		t.Fatalf("the run applied %v, want just %s", applied, budgetSafeguardStep)
	}

	if got := rows(); got != 2 {
		t.Errorf("rows after the step = %d, want 2: widening a CHECK is no data move", got)
	}
	if err := insert("room-1", "budget"); err != nil {
		t.Fatalf("budget with a room was refused after the step: %v", err)
	}
	if got := rows(); got != 3 {
		t.Errorf("rows after the budget insert = %d, want 3", got)
	}

	wantCheckViolation(insert("room-1", "keeper"), "ck_room_safeguards_safeguard")
	// The scope rule the step leaves alone: budget is room-scoped, so an empty room is still refused.
	wantCheckViolation(insert("", "budget"), "ck_room_safeguards_room")

	// Applying the SQL again bypasses the ledger, the same way the 0004 case proves its own guard.
	if err := exec(embeddedStep(t, budgetSafeguardStep).SQL); err != nil {
		t.Fatalf("the step's SQL failed on a second run: %v", err)
	}
	if err := insert("room-2", "budget"); err != nil {
		t.Errorf("budget was refused after the step ran twice: %v", err)
	}
}

// A database whose catalogue does not hold the table is the ordinary state before the registry creates
// its tables. An unguarded DROP/ADD there is SQLSTATE 42P01, which takes the whole boot down; the step
// must find nothing and leave nothing behind.
func TestTheBudgetStepIsANoOpWithoutTheTable(t *testing.T) {
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

	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{embeddedStep(t, budgetSafeguardStep)}}
	if _, err := runner.Apply(ctx); err != nil {
		t.Fatalf("the step failed on a database without its table: %v", err)
	}
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, embeddedStep(t, budgetSafeguardStep).SQL)
		return err
	}); err != nil {
		t.Fatalf("the SQL failed on a database without its table: %v", err)
	}
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT coalesce(to_regclass('room_safeguards')::text, '')`).Scan(&name)
	}); err != nil {
		t.Fatal(err)
	}
	if name != "" {
		t.Errorf("the step created %q, want nothing: it widens a CHECK, it does not invent a table", name)
	}
}
