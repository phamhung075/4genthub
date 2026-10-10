package orm

// The safeguard store's two behaviours, both on a real Postgres: 7.3's alert DECISION, which is a
// comparison against the row the table holds, and the upsert itself - one row per key, latest state
// wins. The socket-level cases (the frame, the offline re-send, the dead-man) live in
// fastmcp/server/httpapp/ws_rigd_test.go; these are the store's own.

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	rigdb "agenthub/fastmcp/rig_safeguard/infrastructure/database"
	"agenthub/fastmcp/session_stream/testdb"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func safeguardRow(rig, state string, restarts int64) rigdb.RigSafeguardORM {
	return rigdb.RigSafeguardORM{
		UserID: "user1", ConnectorID: "conn1", Rig: rig, Safeguard: rigdb.SafeguardCompact,
		State: state, PID: new(4242), Restarts: restarts, AgeS: 31,
		LastBeatAt: new(time.Date(2026, 10, 11, 9, 0, 0, 0, time.UTC)),
	}
}

func storedSafeguard(t *testing.T, sessions *database.SessionManager, row rigdb.RigSafeguardORM) rigdb.RigSafeguardORM {
	t.Helper()
	var stored rigdb.RigSafeguardORM
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT user_id, connector_id, rig, safeguard, state, pid, restarts, age_s, last_beat_at `+
				`FROM rig_safeguards WHERE user_id = $1 AND connector_id = $2 AND rig = $3 AND safeguard = $4`,
			row.UserID, row.ConnectorID, row.Rig, row.Safeguard).Scan(
			&stored.UserID, &stored.ConnectorID, &stored.Rig, &stored.Safeguard, &stored.State,
			&stored.PID, &stored.Restarts, &stored.AgeS, &stored.LastBeatAt)
	}); err != nil {
		t.Fatal(err)
	}
	return stored
}

func safeguardRowCount(t *testing.T, sessions *database.SessionManager, row rigdb.RigSafeguardORM) int {
	t.Helper()
	count := 0
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM rig_safeguards WHERE user_id = $1 AND connector_id = $2`,
			row.UserID, row.ConnectorID).Scan(&count)
	}); err != nil {
		t.Fatal(err)
	}
	return count
}

// TestUpsertAlertsOnlyOnTheRuledTransitions is 7.3's decision table. Each case writes a previous row
// and then the next one, and asserts whether the NEXT write reported an alert - which is what makes
// "re-sent rows produce no duplicate alerts" a measurement rather than a claim.
func TestUpsertAlertsOnlyOnTheRuledTransitions(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()

	cases := []struct {
		name                   string
		prev, next             string
		prevRestarts, restarts int64
		want                   bool
	}{
		{"the first row for a key alerts nothing", "", rigdb.StateRunning, 0, 0, false},
		{"running -> running alerts nothing", rigdb.StateRunning, rigdb.StateRunning, 0, 0, false},
		{"running -> stopped alerts", rigdb.StateRunning, rigdb.StateStopped, 0, 0, true},
		{"running -> silent alerts", rigdb.StateRunning, rigdb.StateSilent, 0, 0, true},
		{"running -> failing alerts", rigdb.StateRunning, rigdb.StateFailing, 0, 0, true},
		{"stopped -> silent alerts nothing", rigdb.StateStopped, rigdb.StateSilent, 0, 0, false},
		{"silent -> running alerts nothing", rigdb.StateSilent, rigdb.StateRunning, 0, 0, false},
		{"failing -> failing alerts nothing", rigdb.StateFailing, rigdb.StateFailing, 0, 0, false},
		{"restarts going up alerts", rigdb.StateStopped, rigdb.StateStopped, 1, 2, true},
		{"restarts standing still alerts nothing", rigdb.StateStopped, rigdb.StateStopped, 2, 2, false},
		{"restarts going up while running alerts", rigdb.StateRunning, rigdb.StateRunning, 0, 1, true},
	}
	for i, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			// Each case gets its own key: the comparisons are against stored rows, so sharing one
			// key would make the cases depend on each other's order.
			rig := fmt.Sprintf("rig-%d", i)
			if c.prev != "" {
				if _, err := Upsert(ctx, sessions, safeguardRow(rig, c.prev, c.prevRestarts)); err != nil {
					t.Fatal(err)
				}
			}
			got, err := Upsert(ctx, sessions, safeguardRow(rig, c.next, c.restarts))
			if err != nil {
				t.Fatal(err)
			}
			if got != c.want {
				t.Errorf("alert = %v, want %v", got, c.want)
			}
			// The write happened either way: an unalerted transition is still stored.
			if stored := storedSafeguard(t, sessions, safeguardRow(rig, c.next, c.restarts)); stored.State != c.next {
				t.Errorf("stored state = %q, want %q", stored.State, c.next)
			}
		})
	}
}

// TestUpsertKeepsOneRowPerKeyAndTheLatestState: the frame is an upsert on
// (user_id, connector_id, rig, safeguard) with no history, so a re-sent row leaves ONE row, and the
// newest report is what the next comparison reads.
func TestUpsertKeepsOneRowPerKeyAndTheLatestState(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	running := safeguardRow("rig-1", rigdb.StateRunning, 0)

	alert, err := Upsert(ctx, sessions, running)
	if err != nil || alert {
		t.Fatalf("first upsert: alert = %v err = %v, want no alert", alert, err)
	}
	if alert, err = Upsert(ctx, sessions, running); err != nil || alert {
		t.Fatalf("re-sent upsert: alert = %v err = %v, want no alert", alert, err)
	}
	if got := safeguardRowCount(t, sessions, running); got != 1 {
		t.Fatalf("rows = %d, want 1", got)
	}

	// A silent safeguard writes over the running one and alerts once; the pid goes null because the
	// process is not running, and last_beat_at is the frame's own beat.
	silent := safeguardRow("rig-1", rigdb.StateSilent, 1)
	silent.PID = nil
	silent.AgeS = 47
	alert, err = Upsert(ctx, sessions, silent)
	if err != nil {
		t.Fatal(err)
	}
	if !alert {
		t.Fatal("running -> silent must alert")
	}
	stored := storedSafeguard(t, sessions, silent)
	if stored.State != rigdb.StateSilent || stored.AgeS != 47 || stored.Restarts != 1 {
		t.Errorf("stored row = %+v, want the newest report", stored)
	}
	if stored.PID != nil {
		t.Errorf("stored pid = %v, want null", *stored.PID)
	}
	if stored.LastBeatAt == nil || !stored.LastBeatAt.Equal(*silent.LastBeatAt) {
		t.Errorf("stored last_beat_at = %v, want the frame's at %v", stored.LastBeatAt, silent.LastBeatAt)
	}
	if got := safeguardRowCount(t, sessions, running); got != 1 {
		t.Fatalf("rows after the update = %d, want 1", got)
	}
}

// TestUpsertRefusesTheClosedSetsBeforeAnyStatement: 7.6's four states and four safeguards are
// checked in the store, so an unknown value is the frame's error rather than a constraint violation
// surfacing as an internal one, and nothing is stored.
func TestUpsertRefusesTheClosedSetsBeforeAnyStatement(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()

	cases := []struct {
		name string
		mut  func(*rigdb.RigSafeguardORM)
		want string
	}{
		{"an unknown state", func(r *rigdb.RigSafeguardORM) { r.State = "paused" }, "bad state"},
		{"an unknown safeguard", func(r *rigdb.RigSafeguardORM) { r.Safeguard = "keeper" }, "bad safeguard"},
		{"a missing rig", func(r *rigdb.RigSafeguardORM) { r.Rig = "" }, "bad rig"},
		{"a rig past the column", func(r *rigdb.RigSafeguardORM) { r.Rig = strings.Repeat("r", 256) }, "bad rig"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			row := safeguardRow("rig-1", rigdb.StateRunning, 0)
			c.mut(&row)
			alert, err := Upsert(ctx, sessions, row)
			var ve *tmvo.ValueError
			if !errors.As(err, &ve) || ve.Msg != c.want {
				t.Fatalf("err = %v, want ValueError %q", err, c.want)
			}
			if alert {
				t.Error("a refused row must not alert")
			}
		})
	}
	if got := safeguardRowCount(t, sessions, safeguardRow("rig-1", rigdb.StateRunning, 0)); got != 0 {
		t.Fatalf("rows after four refused frames = %d, want 0", got)
	}
}
