package session_stream

import (
	"context"
	"errors"
	"log/slog"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestSessionIDFor(t *testing.T) {
	cases := []struct {
		user, connector, key, want string
	}{
		{"user1", "conn1", "key1", "4cafc727-23b6-5e7f-b06b-7728464564bc"},
		{"user-550e8400-e29b-41d4-a716-446655440002", "connector-1", "tmux-0", "22c53896-1078-56c0-a150-14a919520e5c"},
		{"u", "c", "k", "d803d566-e889-5b89-ad33-080508302436"},
		{"alice", "machineA", "%0", "4163ba3f-5bc0-54d4-9aa3-8d909b8ee7d2"},
		{"", "", "", "14f7afad-71de-5e96-81a7-e42b52ef5a74"},
	}
	for _, c := range cases {
		if got := SessionIDFor(c.user, c.connector, c.key); got != c.want {
			t.Errorf("SessionIDFor(%q,%q,%q) = %s, want %s", c.user, c.connector, c.key, got, c.want)
		}
	}
}

func TestClip(t *testing.T) {
	if got := clip(nil); got != nil {
		t.Errorf("clip(nil) = %v, want nil", *got)
	}
	empty := ""
	if got := clip(&empty); got != nil {
		t.Errorf("clip(\"\") = %v, want nil", *got)
	}
	short := "hello"
	if got := clip(&short); got == nil || *got != "hello" {
		t.Errorf("clip(short) = %v", got)
	}
	long := strings.Repeat("é", 300)
	got := clip(&long)
	if got == nil || len([]rune(*got)) != 255 {
		t.Errorf("clip(long) rune length = %d, want 255", len([]rune(*got)))
	}
}

func TestAppendEventsBatchLimit(t *testing.T) {
	_, err := AppendEvents(context.Background(), nil, "u", "s", make([]any, MaxEventsPerBatch+1))
	var ve *tmvo.ValueError
	if !errors.As(err, &ve) || ve.Msg != "at most 200 events per batch" {
		t.Fatalf("err = %v, want ValueError 'at most 200 events per batch'", err)
	}
}

func TestMarkOfflineWithoutSessions(t *testing.T) {
	DefaultSessions = nil
	err := MarkOffline(context.Background(), nil, "u", "c")
	if err == nil || err.Error() != "database configuration not available" {
		t.Fatalf("err = %v", err)
	}
}

func event(typ string, payload any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", typ)
	m.Set("payload", payload)
	return m
}

// The pair a connector reports: HALF of one is refused, because it is ambiguous and the table's own
// CHECK could not store it - but a WHOLE pair that cannot be addressed loses the annotation and
// keeps the session, so an unaddressable rig name never costs a connector its event stream. No
// database is needed - the rule is checked before any statement is built.
func TestSeatIdentityRefusesHalfAPairAndDropsAnUnaddressableOne(t *testing.T) {
	if room, seat, dropped, err := seatIdentity(nil, nil); room != nil || seat != nil || dropped || err != nil {
		t.Errorf("neither reported: got %v, %v, dropped=%v, err=%v - want all empty", room, seat, dropped, err)
	}
	for _, c := range []struct {
		name       string
		room, seat *string
	}{
		{"room without seat", new("dev"), nil},
		{"seat without room", nil, new("alice")},
		{"an empty room beside a seat", new(""), new("alice")},
	} {
		if room, seat, dropped, err := seatIdentity(c.room, c.seat); err == nil {
			t.Errorf("%s: got %v, %v, dropped=%v with no error, want a refusal", c.name, room, seat, dropped)
		} else if !strings.Contains(err.Error(), "room") && !strings.Contains(err.Error(), "seat") {
			t.Errorf("%s: error = %v, want it to name the rule", c.name, err)
		}
	}
	room, key, dropped, err := seatIdentity(new("dev"), new("alice"))
	if err != nil || dropped || room == nil || key == nil || *room != "dev" || *key != "alice" {
		t.Errorf("a whole pair must pass through: %v, %v, dropped=%v, %v", room, key, dropped, err)
	}
	// namePattern is OpenRig's POD OR MEMBER ID rule, and room_slug carries a RIG name - a rig the
	// server did not render may be named anything, so the annotation goes and nothing else does.
	for _, c := range []struct {
		name       string
		room, seat *string
	}{
		{"a rig name that carries a dot", new("4genthub.dev"), new("go-dev")},
		{"a rig name that carries a space", new("not a room"), new("alice")},
		{"a member that cannot name one", new("dev"), new("-lead")},
	} {
		room, seat, dropped, err := seatIdentity(c.room, c.seat)
		if err != nil || !dropped || room != nil || seat != nil {
			t.Errorf("%s: got %v, %v, dropped=%v, err=%v - want the pair dropped with no error", c.name, room, seat, dropped, err)
		}
	}
}

// A dropped pair is not a shrug: the warning is the only trace of what was discarded, so it names
// both halves exactly as the frame sent them - that is what tells an operator which rig could not
// be addressed. A two-value swap here would leave the log silent about the values it is about.
func TestDroppedSeatPairWarnsWithBothValues(t *testing.T) {
	rec := &recordingHandler{}
	prev := slog.Default()
	slog.SetDefault(slog.New(rec))
	defer slog.SetDefault(prev)

	warnUnaddressableSeatPair("key1", "conn1", "4genthub.dev", "go-dev")

	if len(rec.records) != 1 {
		t.Fatalf("records = %d, want exactly 1", len(rec.records))
	}
	got := rec.records[0]
	if got.Level != slog.LevelWarn {
		t.Errorf("level = %v, want warn", got.Level)
	}
	fields := map[string]string{}
	got.Attrs(func(a slog.Attr) bool { fields[a.Key] = a.Value.String(); return true })
	for k, want := range map[string]string{
		"session_key": "key1", "connector_id": "conn1", "room_slug": "4genthub.dev", "seat_key": "go-dev",
	} {
		if fields[k] != want {
			t.Errorf("%s = %q, want %q", k, fields[k], want)
		}
	}
}

// recordingHandler keeps the records a logger emitted, so a test can read a warning as a fact.
type recordingHandler struct{ records []slog.Record }

func (h *recordingHandler) Enabled(context.Context, slog.Level) bool { return true }

func (h *recordingHandler) Handle(_ context.Context, r slog.Record) error {
	h.records = append(h.records, r)
	return nil
}

func (h *recordingHandler) WithAttrs([]slog.Attr) slog.Handler { return h }

func (h *recordingHandler) WithGroup(string) slog.Handler { return h }

func TestRepositoryPostgres(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	user := "user1"
	connector := "conn1"
	key := "key1"
	sid := SessionIDFor(user, connector, key)

	project := "proj"
	room, seat := "dev", "alice"
	row, err := UpsertSession(ctx, sessions, user, connector, key, "name", &project, &room, &seat)
	if err != nil {
		t.Fatal(err)
	}
	wantKeys := []string{"id", "name", "project", "status", "connector_id", "last_seq", "created_at", "last_seen", "room_slug", "seat_key"}
	if got := row.Keys(); strings.Join(got, ",") != strings.Join(wantKeys, ",") {
		t.Fatalf("row keys = %v, want %v", got, wantKeys)
	}
	if v, _ := row.Get("id"); v != sid {
		t.Errorf("id = %v, want %s", v, sid)
	}
	if v, _ := row.Get("status"); v != "active" {
		t.Errorf("status = %v", v)
	}
	if v, _ := row.Get("last_seq"); v != int64(0) {
		t.Errorf("last_seq = %v", v)
	}
	if v, _ := row.Get("created_at"); v == nil {
		t.Errorf("created_at is nil")
	}

	// A different user has a different deterministic id and cannot see user1's row.
	rowOther, err := UpsertSession(ctx, sessions, "user2", connector, key, "n", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if otherID, _ := rowOther.Get("id"); otherID == sid {
		t.Fatalf("user2 got user1's id")
	}
	if g, _ := GetSessionForUser(ctx, sessions, "user2", sid); g != nil {
		t.Fatalf("user2 must not see user1 session: %v", g)
	}

	// Update keeps project when the new one is empty, updates name.
	empty := ""
	row2, err := UpsertSession(ctx, sessions, user, connector, key, "renamed", &empty, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := row2.Get("name"); v != "renamed" {
		t.Errorf("name = %v", v)
	}
	if v, _ := row2.Get("project"); v != "proj" {
		t.Errorf("project = %v, want proj (kept)", v)
	}
	if v, _ := row2.Get("room_slug"); v != "dev" {
		t.Errorf("room_slug = %v, want dev (kept: the frame carried no pair)", v)
	}
	if v, _ := row2.Get("seat_key"); v != "alice" {
		t.Errorf("seat_key = %v, want alice (kept: the frame carried no pair)", v)
	}

	// A frame that names BOTH halves but cannot address them KEEPS THE SESSION and drops the pair:
	// the session still exists, and the identity the connector carried is gone rather than stored
	// raw. This is what a rig the server never rendered reaches - namePattern is the pod-or-member
	// rule, while room_slug holds a rig name.
	badRoom, badSeat := "4genthub.dev", "go-dev"
	droppedRow, err := UpsertSession(ctx, sessions, user, connector, key, "renamed", nil, &badRoom, &badSeat)
	if err != nil {
		t.Fatalf("an unaddressable pair must not refuse the frame: %v", err)
	}
	if v, _ := droppedRow.Get("room_slug"); v != nil {
		t.Errorf("room_slug = %v, want nil (the pair was not addressable)", v)
	}
	if v, _ := droppedRow.Get("seat_key"); v != nil {
		t.Errorf("seat_key = %v, want nil", v)
	}
	storedRow, err := GetSessionForUser(ctx, sessions, user, sid)
	if err != nil || storedRow == nil {
		t.Fatalf("the session must still exist after an unaddressable pair: %v, %v", storedRow, err)
	}
	if v, _ := storedRow.Get("room_slug"); v != nil {
		t.Errorf("stored room_slug = %v, want nil", v)
	}
	if v, _ := storedRow.Get("seat_key"); v != nil {
		t.Errorf("stored seat_key = %v, want nil", v)
	}

	// Append assigns seq server-side.
	p1 := entities.NewOrderedMap[any]()
	p1.Set("text", "one")
	p2 := entities.NewOrderedMap[any]()
	p2.Set("text", "two")
	stored, err := AppendEvents(ctx, sessions, user, sid, []any{event("message", p1), event("output", p2)})
	if err != nil {
		t.Fatal(err)
	}
	if len(stored) != 2 {
		t.Fatalf("stored = %d", len(stored))
	}
	if v, _ := stored[0].Get("seq"); v != int64(1) {
		t.Errorf("seq[0] = %v", v)
	}
	if v, _ := stored[1].Get("seq"); v != int64(2) {
		t.Errorf("seq[1] = %v", v)
	}
	if v, _ := stored[1].Get("type"); v != "output" {
		t.Errorf("type[1] = %v", v)
	}
	if got := stored[0].Keys(); strings.Join(got, ",") != "seq,type,payload" {
		t.Errorf("stored keys = %v", got)
	}

	// Non-object events are rejected.
	_, err = AppendEvents(ctx, sessions, user, sid, []any{"nope"})
	var ve *tmvo.ValueError
	if !errors.As(err, &ve) || ve.Msg != "each event must be an object" {
		t.Fatalf("non-object event err = %v", err)
	}

	// Unknown session is a PermissionError.
	var pe *PermissionError
	_, err = AppendEvents(ctx, sessions, user, "00000000-0000-0000-0000-000000000000", []any{event("message", p1)})
	if !errors.As(err, &pe) || pe.Msg != "unknown session" {
		t.Fatalf("unknown session err = %v", err)
	}

	// Oversized payload becomes {"truncated": true}.
	big := entities.NewOrderedMap[any]()
	big.Set("x", strings.Repeat("a", MaxPayloadChars))
	storedBig, err := AppendEvents(ctx, sessions, user, sid, []any{event("message", big)})
	if err != nil {
		t.Fatal(err)
	}
	payloadVal, _ := storedBig[0].Get("payload")
	payload := payloadVal.(*entities.OrderedMap[any])
	if pv, ok := payload.Get("truncated"); !ok || pv != true {
		t.Fatalf("oversized payload = %v, want truncated marker", payloadVal)
	}

	// Listing returns the events in seq order with keys seq,type,payload,ts.
	events, err := ListEvents(ctx, sessions, user, sid, 0, 500)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 3 {
		t.Fatalf("events = %d, want 3", len(events))
	}
	if got := events[0].Keys(); strings.Join(got, ",") != "seq,type,payload,ts" {
		t.Errorf("event keys = %v", got)
	}
	if v, _ := events[2].Get("seq"); v != int64(3) {
		t.Errorf("last seq = %v", v)
	}
	// after_seq filters.
	after, err := ListEvents(ctx, sessions, user, sid, 1, 500)
	if err != nil {
		t.Fatal(err)
	}
	if len(after) != 2 {
		t.Fatalf("after_seq events = %d, want 2", len(after))
	}

	got, err := GetSessionForUser(ctx, sessions, user, sid)
	if err != nil || got == nil {
		t.Fatalf("get session = %v, %v", got, err)
	}
	if _, err := GetSessionForUser(ctx, sessions, "user2", sid); err != nil {
		t.Fatalf("other user get err = %v", err)
	}
	if g, _ := GetSessionForUser(ctx, sessions, "user2", sid); g != nil {
		t.Fatalf("user2 must not see user1 session: %v", g)
	}

	if err := MarkOffline(ctx, sessions, user, connector); err != nil {
		t.Fatal(err)
	}
	off, _ := GetSessionForUser(ctx, sessions, user, sid)
	if v, _ := off.Get("status"); v != "offline" {
		t.Errorf("status = %v, want offline", v)
	}

	list, err := ListSessions(ctx, sessions, user)
	if err != nil || len(list) != 1 {
		t.Fatalf("list sessions = %v, %v", list, err)
	}

	// Defensive branch: a stored row with the same determinant id but another user_id
	// (only reachable with corrupted/foreign rows).
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, "UPDATE agent_sessions SET user_id = $1 WHERE id = $2", "intruder", sid)
		return err
	}); err != nil {
		t.Fatal(err)
	}
	_, err = UpsertSession(ctx, sessions, user, connector, key, "x", nil, nil, nil)
	if !errors.As(err, &pe) || pe.Msg != "session belongs to another user" {
		t.Fatalf("foreign row upsert err = %v", err)
	}
}

// Python: test_model_timestamps_are_naive_utc. A Go time.Time always carries a location,
// so the ported property is the one the API exposes: created_at and last_seen render as
// naive UTC with no zone designator, like the Python naive datetimes.
func TestSessionTimestampsRenderAsNaiveUTC(t *testing.T) {
	sessions := testdb.NewSessions(t)
	ctx := context.Background()
	row, err := UpsertSession(ctx, sessions, "user1", "conn1", "key1", "name", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"created_at", "last_seen"} {
		v, _ := row.Get(key)
		s, ok := v.(string)
		if !ok {
			t.Fatalf("%s = %v, want an ISO string", key, v)
		}
		if strings.ContainsAny(s, "Zz+") {
			t.Errorf("%s = %q, want naive UTC with no zone designator", key, s)
		}
		if _, err := time.Parse("2006-01-02T15:04:05", strings.SplitN(s, ".", 2)[0]); err != nil {
			t.Errorf("%s = %q is not an ISO timestamp: %v", key, s, err)
		}
	}
}
