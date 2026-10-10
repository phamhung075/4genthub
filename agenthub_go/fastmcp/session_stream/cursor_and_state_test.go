package session_stream

// The two columns rigd's phase 1 adds to agent_sessions, measured on a real Postgres at the level
// the store owns: client_cursor commits WITH the batch it describes, and seat_state moves only when
// a frame reports one (rigd-boundaries.md 2.1 option A, 2.2, 2.3a).
//
// The socket-level cases - a lost ack, the resume, the row the browser reads - live in
// fastmcp/server/httpapp/ws_rigd_test.go; these are the store's, so a change to the transaction can
// fail here without a websocket in the way.

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/session_stream/testdb"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func storedCursor(t *testing.T, sessions *database.SessionManager, sessionID string) *string {
	t.Helper()
	var cursor *string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, "SELECT client_cursor FROM agent_sessions WHERE id = $1", sessionID).Scan(&cursor)
	}); err != nil {
		t.Fatal(err)
	}
	return cursor
}

// TestAppendEventsCommitsTheCursorWithTheBatch: the cursor and the events are one transaction, so a
// batch that exists has a cursor that moved with it - which is exactly what a lost ack relies on
// (2.1, option A). A frame that carries NO cursor stores null, because the client's position is then
// unknown and the session must say so rather than keep a stale one.
func TestAppendEventsCommitsTheCursorWithTheBatch(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	user, connector, key := "user1", "conn1", "seat/lead"
	upsert, err := UpsertSession(ctx, sessions, user, connector, key, "name", nil, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	sid, _ := upsert.Row.Get("id")
	sessionID := sid.(string)
	if upsert.Cursor != nil {
		t.Fatalf("a fresh session's cursor = %v, want null", *upsert.Cursor)
	}

	batch := []any{event("message", nil)}
	stored, cursor, err := AppendEvents(ctx, sessions, user, sessionID, batch, new("transcript:4096"))
	if err != nil {
		t.Fatal(err)
	}
	if len(stored) != 1 {
		t.Fatalf("stored = %d, want 1", len(stored))
	}
	if cursor == nil || *cursor != "transcript:4096" {
		t.Fatalf("returned cursor = %v, want transcript:4096", cursor)
	}
	if got := storedCursor(t, sessions, sessionID); got == nil || *got != "transcript:4096" {
		t.Fatalf("stored cursor = %v, want transcript:4096", got)
	}

	// The next frame carries none: the stored position becomes null rather than staying behind.
	if _, cursor, err = AppendEvents(ctx, sessions, user, sessionID, batch, nil); err != nil {
		t.Fatal(err)
	}
	if cursor != nil {
		t.Fatalf("returned cursor = %v, want null", *cursor)
	}
	if got := storedCursor(t, sessions, sessionID); got != nil {
		t.Fatalf("stored cursor = %v, want null", *got)
	}

	// The register frame reports the stored cursor back, which is how a reconnect resumes.
	again, err := UpsertSession(ctx, sessions, user, connector, key, "name", nil, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if again.Cursor != nil {
		t.Fatalf("session frame reported cursor = %v, want null", *again.Cursor)
	}
	// A cursor of EXACTLY the bound is accepted: 2.2 says "at most 512 bytes", so the bound is a
	// maximum rather than an exclusive one.
	atBound := strings.Repeat("c", MaxCursorBytes)
	if _, _, err := AppendEvents(ctx, sessions, user, sessionID, batch, &atBound); err != nil {
		t.Fatalf("a cursor of exactly %d bytes must be accepted: %v", MaxCursorBytes, err)
	}
	again, err = UpsertSession(ctx, sessions, user, connector, key, "name", nil, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if again.Cursor == nil || *again.Cursor != atBound {
		t.Fatalf("session frame reported cursor = %v, want the %d-byte cursor", again.Cursor, MaxCursorBytes)
	}
}

// TestAppendEventsRefusesACursorPastItsByteBound: 2.2 bounds the opaque cursor at 512 BYTES, and the
// refusal is the store's, so nothing that bypasses the socket can store a longer one.
func TestAppendEventsRefusesACursorPastItsByteBound(t *testing.T) {
	_, _, err := AppendEvents(context.Background(), nil, "u", "s", []any{}, new(strings.Repeat("c", MaxCursorBytes+1)))
	var ve *tmvo.ValueError
	if !errors.As(err, &ve) || ve.Msg != "cursor is too long" {
		t.Fatalf("err = %v, want ValueError 'cursor is too long'", err)
	}
}

// TestSeatStateIsReportedAndKeptWhenAbsent: 2.3a's column, at the store. A frame that reports a state
// writes it; a frame that reports none keeps what an earlier one said, so an old client cannot erase
// a state a rigd reported; and a value outside the ruled two is refused before any statement runs.
func TestSeatStateIsReportedAndKeptWhenAbsent(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	user, connector, key := "user1", "conn1", "seat/lead"

	up, err := UpsertSession(ctx, sessions, user, connector, key, "name", nil, nil, nil, new("running"))
	if err != nil {
		t.Fatal(err)
	}
	id, _ := up.Row.Get("id")
	sessionID := id.(string)
	if got, _ := up.Row.Get("seat_state"); got != "running" {
		t.Fatalf("seat_state = %v, want running", got)
	}

	// No state: the reported one stays.
	up, err = UpsertSession(ctx, sessions, user, connector, key, "renamed", nil, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := up.Row.Get("seat_state"); got != "running" {
		t.Fatalf("seat_state after a frame with no state = %v, want running (kept)", got)
	}

	up, err = UpsertSession(ctx, sessions, user, connector, key, "renamed", nil, nil, nil, new("stopped"))
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := up.Row.Get("seat_state"); got != "stopped" {
		t.Fatalf("seat_state = %v, want stopped", got)
	}

	_, err = UpsertSession(ctx, sessions, user, connector, key, "renamed", nil, nil, nil, new("paused"))
	var ve *tmvo.ValueError
	if !errors.As(err, &ve) || ve.Msg != "bad state" {
		t.Fatalf("err = %v, want ValueError 'bad state'", err)
	}
	stored, err := GetSessionForUser(ctx, sessions, user, sessionID)
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := stored.Get("seat_state"); got != "stopped" {
		t.Fatalf("stored seat_state after a refused value = %v, want stopped", got)
	}
}
