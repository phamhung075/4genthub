package websocket

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeWebSocket struct {
	accepted    bool
	closeCode   int
	closeReason string
	sent        []string
	sendErr     error
	receiveErr  error
	receiveQ    []string
}

func (f *fakeWebSocket) Accept(ctx context.Context) error { f.accepted = true; return nil }
func (f *fakeWebSocket) Close(ctx context.Context, code int, reason string) error {
	f.closeCode, f.closeReason = code, reason
	return nil
}
func (f *fakeWebSocket) SendText(ctx context.Context, data string) error {
	if f.sendErr != nil {
		return f.sendErr
	}
	f.sent = append(f.sent, data)
	return nil
}
func (f *fakeWebSocket) ReceiveText(ctx context.Context) (string, error) {
	if len(f.receiveQ) > 0 {
		msg := f.receiveQ[0]
		f.receiveQ = f.receiveQ[1:]
		return msg, nil
	}
	if f.receiveErr != nil {
		return "", f.receiveErr
	}
	return "", &WebSocketDisconnect{Code: 1000}
}

func TestConnectionManagerConnectDisconnect(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	ws := &fakeWebSocket{}

	sid, err := cm.Connect(ctx, ws, "u1", nil)
	if err != nil {
		t.Fatalf("Connect: %v", err)
	}
	if !ws.accepted || sid == "" {
		t.Fatalf("Connect accepted=%v sid=%q", ws.accepted, sid)
	}
	if !cm.IsUserConnected("u1") {
		t.Fatalf("u1 should be connected")
	}

	stats := cm.GetConnectionStats()
	if v, _ := stats.Get("total_connections"); v != 1 {
		t.Fatalf("total_connections = %v", v)
	}
	if v, _ := stats.Get("active_users"); lenOf(v) != 1 {
		t.Fatalf("active_users = %v", v)
	}
	sessions, _ := stats.Get("sessions")
	sessionMap := sessions.(*entities.OrderedMap[any])
	userSessionsAny, _ := sessionMap.Get("user_sessions")
	userSessions := userSessionsAny.(*entities.OrderedMap[any])
	if got, _ := userSessions.Get("u1"); got != sid {
		t.Fatalf("user_sessions[u1] = %v, want %v", got, sid)
	}

	if got := cm.NextSequence(); got != 1 {
		t.Fatalf("NextSequence = %d, want 1", got)
	}
	if got := cm.NextSequence(); got != 2 {
		t.Fatalf("NextSequence = %d, want 2", got)
	}

	cm.Disconnect(ctx, "u1")
	if ws.closeCode != 1000 {
		t.Fatalf("close code = %d, want 1000", ws.closeCode)
	}
	if cm.IsUserConnected("u1") {
		t.Fatalf("u1 should be disconnected")
	}
	if v, _ := cm.GetConnectionStats().Get("total_connections"); v != 0 {
		t.Fatalf("total_connections = %v, want 0", v)
	}
}

func TestBroadcastImmediateDisconnectsFailures(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	good := &fakeWebSocket{}
	bad := &fakeWebSocket{sendErr: &WebSocketDisconnect{Code: 1006}}
	if _, err := cm.Connect(ctx, good, "u1", nil); err != nil {
		t.Fatal(err)
	}
	if _, err := cm.Connect(ctx, bad, "u2", nil); err != nil {
		t.Fatal(err)
	}

	cm.BroadcastImmediate(ctx, CreateHeartbeat(nil, 1))
	if len(good.sent) != 1 {
		t.Fatalf("good websocket received %d messages, want 1", len(good.sent))
	}
	if cm.IsUserConnected("u2") {
		t.Fatalf("failed websocket should be disconnected")
	}
	if !cm.IsUserConnected("u1") {
		t.Fatalf("good websocket should remain connected")
	}
}

func TestProcessMessageInvalidJSON(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	ws := &fakeWebSocket{}
	sid, _ := cm.Connect(ctx, ws, "u1", nil)

	cm.ProcessMessage(ctx, "u1", "not json")
	if len(ws.sent) != 1 {
		t.Fatalf("sent %d messages, want 1", len(ws.sent))
	}
	sent := ws.sent[0]
	if !strings.Contains(sent, `"type":"error"`) || !strings.Contains(sent, "Invalid JSON: ") {
		t.Fatalf("unexpected error message: %s", sent)
	}
	if !strings.Contains(sent, `"session_id":"`+sid+`"`) {
		t.Fatalf("error message missing session id: %s", sent)
	}
}

func TestProcessMessageUserBroadcastsUpdate(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	ws := &fakeWebSocket{}
	if _, err := cm.Connect(ctx, ws, "u1", nil); err != nil {
		t.Fatal(err)
	}

	raw := `{"version":"2.0","type":"update","sequence":1,"payload":{"entity":"task","action":"update","data":{"primary":{"id":"t1"}}},"metadata":{"source":"user"}}`
	cm.ProcessMessage(ctx, "u1", raw)
	if len(ws.sent) != 1 {
		t.Fatalf("sent %d messages, want 1", len(ws.sent))
	}
	if !strings.Contains(ws.sent[0], `"type":"update"`) || !strings.Contains(ws.sent[0], `"source":"user"`) {
		t.Fatalf("unexpected broadcast: %s", ws.sent[0])
	}
}

func TestProcessMessageQueuesAIMessage(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	raw := `{"version":"2.0","type":"bulk","sequence":1,"payload":{"entity":"task","action":"update","data":{"primary":{"id":"t1"}}},"metadata":{"source":"mcp-ai"}}`
	cm.ProcessMessage(ctx, "u1", raw)
	if got := cm.AIBatchQueue.QSize(); got != 1 {
		t.Fatalf("queue size = %d, want 1", got)
	}
}

func TestConnectionStatsKeyOrder(t *testing.T) {
	cm := NewConnectionManager(nil)
	stats := cm.GetConnectionStats()
	want := []string{"total_connections", "active_users", "queue_size", "sequence_counter", "sessions"}
	got := stats.Keys()
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func TestCleanupDrainsQueueAndDisconnects(t *testing.T) {
	ctx := context.Background()
	cm := NewConnectionManager(nil)
	ws := &fakeWebSocket{}
	if _, err := cm.Connect(ctx, ws, "u1", nil); err != nil {
		t.Fatal(err)
	}
	cm.AIBatchQueue.Put(CreateHeartbeat(nil, 1))

	cm.Cleanup(ctx)
	if cm.IsUserConnected("u1") {
		t.Fatalf("cleanup should disconnect users")
	}
	if cm.AIBatchQueue.QSize() != 0 {
		t.Fatalf("cleanup should drain the queue")
	}
}
