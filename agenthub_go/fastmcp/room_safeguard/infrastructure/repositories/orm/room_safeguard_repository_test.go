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

	rigdb "agenthub/fastmcp/room_safeguard/infrastructure/database"
	"agenthub/fastmcp/session_stream/testdb"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func safeguardRow(room, state string, restarts int64) rigdb.RoomSafeguardORM {
	return rigdb.RoomSafeguardORM{
		UserID: "user1", ConnectorID: "conn1", Room: room, Safeguard: rigdb.SafeguardCompact,
		State: state, PID: new(4242), Restarts: restarts, AgeS: 31,
		LastBeatAt: new(time.Date(2026, 10, 11, 9, 0, 0, 0, time.UTC)),
	}
}

func storedSafeguard(t *testing.T, sessions *database.SessionManager, row rigdb.RoomSafeguardORM) rigdb.RoomSafeguardORM {
	t.Helper()
	var stored rigdb.RoomSafeguardORM
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT user_id, connector_id, room, safeguard, state, pid, restarts, age_s, last_beat_at `+
				`FROM room_safeguards WHERE user_id = $1 AND connector_id = $2 AND room = $3 AND safeguard = $4`,
			row.UserID, row.ConnectorID, row.Room, row.Safeguard).Scan(
			&stored.UserID, &stored.ConnectorID, &stored.Room, &stored.Safeguard, &stored.State,
			&stored.PID, &stored.Restarts, &stored.AgeS, &stored.LastBeatAt)
	}); err != nil {
		t.Fatal(err)
	}
	return stored
}

func safeguardRowCount(t *testing.T, sessions *database.SessionManager, row rigdb.RoomSafeguardORM) int {
	t.Helper()
	count := 0
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM room_safeguards WHERE user_id = $1 AND connector_id = $2`,
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
			room := fmt.Sprintf("room-%d", i)
			if c.prev != "" {
				if _, err := Upsert(ctx, sessions, safeguardRow(room, c.prev, c.prevRestarts)); err != nil {
					t.Fatal(err)
				}
			}
			got, err := Upsert(ctx, sessions, safeguardRow(room, c.next, c.restarts))
			if err != nil {
				t.Fatal(err)
			}
			if got != c.want {
				t.Errorf("alert = %v, want %v", got, c.want)
			}
			// The write happened either way: an unalerted transition is still stored.
			if stored := storedSafeguard(t, sessions, safeguardRow(room, c.next, c.restarts)); stored.State != c.next {
				t.Errorf("stored state = %q, want %q", stored.State, c.next)
			}
		})
	}
}

// TestUpsertKeepsOneRowPerKeyAndTheLatestState: the frame is an upsert on
// (user_id, connector_id, room, safeguard) with no history, so a re-sent row leaves ONE row, and the
// newest report is what the next comparison reads.
func TestUpsertKeepsOneRowPerKeyAndTheLatestState(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	running := safeguardRow("room-1", rigdb.StateRunning, 0)

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
	silent := safeguardRow("room-1", rigdb.StateSilent, 1)
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

// TestUpsertRefusesTheClosedSetsBeforeAnyStatement: 7.6's four states and the seven safeguards (7.2),
// with the room rule each name's scope carries (D2), are checked in the store, so an unknown value is
// the frame's error rather than a constraint violation surfacing as an internal one, and nothing is
// stored.
func TestUpsertRefusesTheClosedSetsBeforeAnyStatement(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()

	cases := []struct {
		name string
		mut  func(*rigdb.RoomSafeguardORM)
		want string
	}{
		{"an unknown state", func(r *rigdb.RoomSafeguardORM) { r.State = "paused" }, "bad state"},
		{"an unknown safeguard", func(r *rigdb.RoomSafeguardORM) { r.Safeguard = "keeper" }, "bad safeguard"},
		{"a room-scoped safeguard with no room", func(r *rigdb.RoomSafeguardORM) { r.Room = "" }, "bad room"},
		{"budget with no room", func(r *rigdb.RoomSafeguardORM) { r.Safeguard = rigdb.SafeguardBudget; r.Room = "" }, "bad room"},
		{"a room-scoped safeguard past the column", func(r *rigdb.RoomSafeguardORM) { r.Room = strings.Repeat("r", 256) }, "bad room"},
		{"a machine-scoped safeguard carrying a room", func(r *rigdb.RoomSafeguardORM) { r.Safeguard = rigdb.SafeguardBridge }, "bad room"},
		{"the machine-scoped agent carrying a room", func(r *rigdb.RoomSafeguardORM) { r.Safeguard = rigdb.SafeguardAgent }, "bad room"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			row := safeguardRow("room-1", rigdb.StateRunning, 0)
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
	if got := safeguardRowCount(t, sessions, safeguardRow("room-1", rigdb.StateRunning, 0)); got != 0 {
		t.Fatalf("rows after %d refused frames = %d, want 0", len(cases), got)
	}
}

// TestUpsertAcceptsEachOfTheSevenNamesInItsScope: D1 and D2, half by half - each of the seven names
// stores with the room its scope demands: a room for the five room-scoped ones, EXACTLY an empty room for
// bridge and agent. This is the shape the client publishes on every ready
// (agenthub_client/internal/clientservices/services.go:114-116), and the three names the old set did
// not hold were refused at every connect; `budget` was the fourth, refused until migration 0009
// widened the CHECK.
//
// It is a store case rather than a validate() case on purpose: what it proves is that the accepted
// halves reach the table, which is where the scope rule also exists as a CHECK.
func TestUpsertAcceptsEachOfTheSevenNamesInItsScope(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()

	cases := []struct{ name, room string }{
		{rigdb.SafeguardCompact, "room-1"},
		{rigdb.SafeguardWatchdog, "room-1"},
		{rigdb.SafeguardMessages, "room-1"},
		{rigdb.SafeguardRoomGuard, "room-1"},
		{rigdb.SafeguardBudget, "room-1"},
		{rigdb.SafeguardBridge, ""},
		{rigdb.SafeguardAgent, ""},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			row := safeguardRow(c.room, rigdb.StateRunning, 0)
			row.Safeguard = c.name
			if _, err := Upsert(ctx, sessions, row); err != nil {
				t.Fatalf("upsert %s with room %q: %v", c.name, c.room, err)
			}
			if stored := storedSafeguard(t, sessions, row); stored.Safeguard != c.name || stored.Room != c.room {
				t.Errorf("stored %s/%q, want %s/%q", stored.Safeguard, stored.Room, c.name, c.room)
			}
		})
	}
}

// TestValidateStatesTheSevenNamesAndTheirScopes is the rule itself, with no database in the way: every
// one of the seven names is read with the room shape its scope allows, and the only other name and the
// only other state are refused. The three messages are the ones the socket turns into
// `bad_rig` / `bad_safeguard` / `bad_state`, which is what the client reads.
func TestValidateStatesTheSevenNamesAndTheirScopes(t *testing.T) {
	row := func(safeguard, room, state string) rigdb.RoomSafeguardORM {
		return rigdb.RoomSafeguardORM{UserID: "user1", ConnectorID: "conn1", Room: room, Safeguard: safeguard, State: state}
	}
	longRig := strings.Repeat("r", 256)
	cases := []struct {
		what string
		row  rigdb.RoomSafeguardORM
		want string
	}{
		{"compact with a room", row(rigdb.SafeguardCompact, "room-1", rigdb.StateRunning), ""},
		{"watchdog with a room", row(rigdb.SafeguardWatchdog, "room-1", rigdb.StateStopped), ""},
		{"messages with a room", row(rigdb.SafeguardMessages, "room-1", rigdb.StateSilent), ""},
		{"roomguard with a room", row(rigdb.SafeguardRoomGuard, "room-1", rigdb.StateFailing), ""},
		{"budget with a room", row(rigdb.SafeguardBudget, "room-1", rigdb.StateRunning), ""},
		{"bridge with no room", row(rigdb.SafeguardBridge, "", rigdb.StateRunning), ""},
		{"agent with no room", row(rigdb.SafeguardAgent, "", rigdb.StateRunning), ""},
		{"compact with no room", row(rigdb.SafeguardCompact, "", rigdb.StateRunning), "bad room"},
		{"messages with no room", row(rigdb.SafeguardMessages, "", rigdb.StateRunning), "bad room"},
		{"budget with no room", row(rigdb.SafeguardBudget, "", rigdb.StateRunning), "bad room"},
		{"a room past the column", row(rigdb.SafeguardWatchdog, longRig, rigdb.StateRunning), "bad room"},
		{"bridge carrying a room", row(rigdb.SafeguardBridge, "room-1", rigdb.StateRunning), "bad room"},
		{"agent carrying a room", row(rigdb.SafeguardAgent, "room-1", rigdb.StateRunning), "bad room"},
		{"the retired rigd name", row("rigd", "room-1", rigdb.StateRunning), "bad safeguard"},
		{"an unknown name", row("keeper", "room-1", rigdb.StateRunning), "bad safeguard"},
		{"an unknown state", row(rigdb.SafeguardCompact, "room-1", "paused"), "bad state"},
	}
	for _, c := range cases {
		t.Run(c.what, func(t *testing.T) {
			err := validate(c.row)
			if c.want == "" {
				if err != nil {
					t.Fatalf("validate = %v, want the row accepted", err)
				}
				return
			}
			var ve *tmvo.ValueError
			if !errors.As(err, &ve) || ve.Msg != c.want {
				t.Fatalf("validate = %v, want ValueError %q", err, c.want)
			}
		})
	}
}
