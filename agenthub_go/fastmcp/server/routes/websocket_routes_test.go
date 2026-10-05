package routes

import (
	"context"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeWS struct {
	sent [][]byte
}

func (f *fakeWS) Accept(ctx context.Context) error { return nil }
func (f *fakeWS) Close(ctx context.Context, code int, reason string) error {
	return nil
}
func (f *fakeWS) SendText(ctx context.Context, data string) error {
	f.sent = append(f.sent, []byte(data))
	return nil
}
func (f *fakeWS) ReceiveText(ctx context.Context) (string, error) { return "", nil }

func strPtr(s string) *string { return &s }

// A seat-domain frame must reach only the owning user's sockets: the seat surface is tenant
// scoped, and this is the boundary a second logged-in user must never cross.
func TestSeatBroadcastReachesOnlyTheOwningUsersSocket(t *testing.T) {
	owner, other := &fakeWS{}, &fakeWS{}
	connectionsMu.Lock()
	connections[owner] = &WebSocketConnection{
		Websocket: owner,
		User:      &authdomain.User{ID: strPtr("u-owner")},
		ClientID:  "c1",
	}
	connections[other] = &WebSocketConnection{
		Websocket: other,
		User:      &authdomain.User{ID: strPtr("u-other")},
		ClientID:  "c2",
	}
	connectionsMu.Unlock()
	defer func() {
		connectionsMu.Lock()
		delete(connections, owner)
		delete(connections, other)
		connectionsMu.Unlock()
	}()

	data := entities.NewOrderedMap[any]()
	data.Set("id", "dev/alice")
	data.Set("room", "dev")
	data.Set("seat_key", "alice")
	if err := BroadcastDataChange(context.Background(), "created", "seat", "dev/alice", "u-owner", data, nil); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}
	if len(owner.sent) != 1 {
		t.Fatalf("the owning user received %d frames, want 1", len(owner.sent))
	}
	for _, f := range other.sent {
		if strings.Contains(string(f), `"entity":"seat"`) {
			t.Fatalf("a second user received another tenant's seat frame: %s", f)
		}
	}
	// The second user is not silently ignored: the existing rules deny and notify, which is the
	// path every other entity takes too.
	if len(other.sent) == 0 {
		t.Fatalf("the second user was not told the event was denied")
	}
	if !strings.Contains(string(other.sent[0]), "authorization_denied") {
		t.Fatalf("second user frame is not the denial: %s", other.sent[0])
	}
	body := string(owner.sent[0])
	for _, want := range []string{`"entity":"seat"`, `"action":"created"`, `"id":"dev/alice"`, `"room":"dev"`, `"seat_key":"alice"`} {
		if !strings.Contains(body, want) {
			t.Fatalf("owner frame missing %s: %s", want, body)
		}
	}
}

func omKeys(t *testing.T, m *entities.OrderedMap[any], want ...string) {
	t.Helper()
	got := m.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func TestBroadcastDataChangeCreatedMessageShape(t *testing.T) {
	ws := &fakeWS{}
	connectionsMu.Lock()
	connections[ws] = &WebSocketConnection{
		Websocket: ws,
		User:      &authdomain.User{ID: strPtr("u1")},
		ClientID:  "c1",
	}
	connectionsMu.Unlock()
	defer func() {
		connectionsMu.Lock()
		delete(connections, ws)
		connectionsMu.Unlock()
	}()

	// Own action: Rule 1 authorizes the triggering user.
	if err := BroadcastDataChange(context.Background(), "created", "task", "t1", "u1", nil, nil); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}
	if len(ws.sent) != 1 {
		t.Fatalf("sent %d messages, want 1", len(ws.sent))
	}
	decoded, err := entities.DecodeJSON(ws.sent[0])
	if err != nil {
		t.Fatalf("DecodeJSON: %v", err)
	}
	msg, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("decoded type %T", decoded)
	}
	omKeys(t, msg, "id", "version", "type", "timestamp", "sequence", "payload", "metadata")
	if v, _ := msg.Get("version"); v != "2.0" {
		t.Fatalf("version = %v", v)
	}
	if v, _ := msg.Get("type"); v != "update" {
		t.Fatalf("type = %v", v)
	}
	payload, _ := msg.Get("payload")
	pm := payload.(*entities.OrderedMap[any])
	omKeys(t, pm, "entity", "action", "data")
	if v, _ := pm.Get("entity"); v != "task" {
		t.Fatalf("entity = %v", v)
	}
	if v, _ := pm.Get("action"); v != "created" {
		t.Fatalf("action = %v", v)
	}
	data, _ := pm.Get("data")
	dm := data.(*entities.OrderedMap[any])
	omKeys(t, dm, "primary")
	if v, ok := dm.Get("primary"); !ok || v != nil {
		t.Fatalf("primary = %v (%v)", v, ok)
	}
	meta, _ := msg.Get("metadata")
	mm := meta.(*entities.OrderedMap[any])
	omKeys(t, mm, "source", "userId", "entity_type", "entity_id", "event_type")
	if v, _ := mm.Get("source"); v != "user" {
		t.Fatalf("source = %v", v)
	}
	if v, _ := mm.Get("userId"); v != "u1" {
		t.Fatalf("userId = %v", v)
	}
	if v, _ := mm.Get("entity_id"); v != "t1" {
		t.Fatalf("entity_id = %v", v)
	}
}

func TestBroadcastDataChangeSystemSourceForUnknownEvent(t *testing.T) {
	ws := &fakeWS{}
	connectionsMu.Lock()
	connections[ws] = &WebSocketConnection{
		Websocket: ws,
		User:      &authdomain.User{ID: strPtr("u1")},
		ClientID:  "c1",
	}
	connectionsMu.Unlock()
	defer func() {
		connectionsMu.Lock()
		delete(connections, ws)
		connectionsMu.Unlock()
	}()

	if err := BroadcastDataChange(context.Background(), "refreshed", "task", "t1", "u1", nil, nil); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}
	decoded, err := entities.DecodeJSON(ws.sent[0])
	if err != nil {
		t.Fatalf("DecodeJSON: %v", err)
	}
	msg := decoded.(*entities.OrderedMap[any])
	meta, _ := msg.Get("metadata")
	mm := meta.(*entities.OrderedMap[any])
	if v, _ := mm.Get("source"); v != "system" {
		t.Fatalf("source = %v, want system", v)
	}
}

func TestIsUserAuthorizedForMessageNoConnection(t *testing.T) {
	ws := &fakeWS{}
	if IsUserAuthorizedForMessage(context.Background(), ws, "task", "t1", "u1", nil) {
		t.Fatal("expected false for unknown connection")
	}
	if len(ws.sent) != 1 {
		t.Fatalf("sent %d error messages, want 1", len(ws.sent))
	}
}
