package websocket

import (
	"context"
	"strings"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeWS struct {
	accepted bool
	state    string
	sentText []string
	sentJSON []any
	mu       sync.Mutex
	received []string
	recvIdx  int
}

func newFakeWS() *fakeWS { return &fakeWS{state: WebSocketStateDisconnected} }

func (f *fakeWS) Accept() error { f.accepted = true; f.state = WebSocketStateConnected; return nil }
func (f *fakeWS) SendText(t string) error {
	f.sentText = append(f.sentText, t)
	return nil
}
func (f *fakeWS) SendJSON(d any) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.sentJSON = append(f.sentJSON, d)
	return nil
}

func (f *fakeWS) jsonCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.sentJSON)
}
func (f *fakeWS) ReceiveText(context.Context) (string, error) {
	if f.recvIdx >= len(f.received) {
		return "", &WebSocketDisconnect{}
	}
	s := f.received[f.recvIdx]
	f.recvIdx++
	return s, nil
}
func (f *fakeWS) ReceiveJSON(context.Context) (any, error) { return nil, &WebSocketDisconnect{} }
func (f *fakeWS) Close() error                             { f.state = WebSocketStateDisconnected; return nil }
func (f *fakeWS) ClientState() string                      { return f.state }

func TestWebSocketMessageRoundTrip(t *testing.T) {
	ts := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	corr := "c1"
	msg := &WebSocketMessage{
		ID: "m1", Type: MessageTypeConnect, FromAgent: "a", ToAgents: []string{"b"},
		Timestamp: ts, Payload: wsObj("k", 1), RequiresAck: true, CorrelationID: &corr,
	}
	text, err := msg.ToJSON()
	if err != nil {
		t.Fatal(err)
	}
	want := `{"id": "m1", "type": "connect", "from_agent": "a", "to_agents": ["b"], "timestamp": "2024-01-02T03:04:05+00:00", "payload": {"k": 1}, "requires_ack": true, "correlation_id": "c1"}`
	if text != want {
		t.Fatalf("to_json = %s", text)
	}

	back, err := FromJSON(text)
	if err != nil {
		t.Fatal(err)
	}
	if back.ID != "m1" || back.Type != MessageTypeConnect || back.FromAgent != "a" {
		t.Fatalf("parsed = %+v", back)
	}
	if len(back.ToAgents) != 1 || back.ToAgents[0] != "b" || !back.RequiresAck {
		t.Fatalf("parsed = %+v", back)
	}
	if !back.Timestamp.Equal(ts) {
		t.Fatalf("timestamp = %v", back.Timestamp)
	}
	if v, _ := back.Payload.Get("k"); v != int64(1) {
		t.Fatalf("payload k = %v (%T)", v, v)
	}
	if back.CorrelationID == nil || *back.CorrelationID != "c1" {
		t.Fatalf("correlation = %v", back.CorrelationID)
	}

	if _, err := ParseMessageType("bogus"); err == nil || err.Error() != "'bogus' is not a valid MessageType" {
		t.Fatalf("parse type error = %v", err)
	}
	if _, err := FromJSON(`{"id":"x"}`); err == nil {
		t.Fatal("missing fields should fail")
	}
}

func TestAgentConnectionIsAlive(t *testing.T) {
	c := NewAgentConnection("a", "s", newFakeWS(), time.Now().UTC(), time.Now().UTC().Add(-30*time.Second))
	if !c.IsAlive(60) {
		t.Fatal("30s < 60s should be alive")
	}
	c.LastHeartbeat = time.Now().UTC().Add(-61 * time.Second)
	if c.IsAlive(60) {
		t.Fatal("61s > 60s should be dead")
	}
}

type fakeTracker struct {
	calls  int
	status any
}

func (f *fakeTracker) UpdateAgentStatus(_ context.Context, _ string, status, _, _, _ any) error {
	f.calls++
	f.status = status
	return nil
}

func TestHubConnectBroadcastAndInfo(t *testing.T) {
	hub := NewAgentCommunicationHub(nil, 30, 30)
	wsA, wsB := newFakeWS(), newFakeWS()
	if err := hub.ConnectAgent("A", "sA", wsA); err != nil {
		t.Fatal(err)
	}
	if err := hub.ConnectAgent("B", "sB", wsB); err != nil {
		t.Fatal(err)
	}
	if hub.Connections.Len() != 2 {
		t.Fatalf("connections = %d", hub.Connections.Len())
	}
	global, _ := hub.Channels.Get("global")
	if global.Len() != 2 {
		t.Fatalf("global = %d", global.Len())
	}
	if len(wsA.sentText) != 2 { // own welcome + agent_connected for B
		t.Fatalf("A messages = %d", len(wsA.sentText))
	}
	if len(wsB.sentText) != 1 { // own welcome only (agent_connected excluded self)
		t.Fatalf("B welcome messages = %d", len(wsB.sentText))
	}
	if v, _ := hub.Metrics.Get("total_connections"); v != 2 {
		t.Fatalf("total_connections = %v", v)
	}

	// A sends a broadcast: B receives it, A does not.
	payload := wsObj("text", "hi")
	if n := hub.BroadcastMessage(MessageTypeBroadcastMessage, payload, []string{"A"}); n != 1 {
		t.Fatalf("broadcast sent = %d", n)
	}
	if len(wsB.sentText) != 2 { // welcome + broadcast
		t.Fatalf("B messages = %d", len(wsB.sentText))
	}
	if !strings.Contains(wsB.sentText[1], `"type": "broadcast_message"`) {
		t.Fatalf("B broadcast = %s", wsB.sentText[1])
	}

	// Channel subscription and targeted send.
	if !hub.SubscribeToChannel("A", "status") {
		t.Fatal("subscribe failed")
	}
	if n := hub.BroadcastToChannel("status", MessageTypeStatusUpdate, wsObj("agent_id", "B"), nil); n != 1 {
		t.Fatalf("channel broadcast = %d", n)
	}
	if hub.BroadcastToChannel("nope", MessageTypeStatusUpdate, wsObj(), nil) != 0 {
		t.Fatal("unknown channel should send 0")
	}

	status := hub.GetConnectionStatus()
	if v, _ := status.Get("active_connections"); v != 2 {
		t.Fatalf("status = %v", v)
	}
	agents, _ := status.Get("agents")
	if strings.Join(agents.([]string), ",") != "A,B" {
		t.Fatalf("agents = %v", agents)
	}
	info := hub.GetAgentInfo("A")
	if info == nil {
		t.Fatal("missing agent info")
	}
	subs, _ := info.Get("subscriptions")
	if strings.Join(subs.([]string), ",") != "status" {
		t.Fatalf("subscriptions = %v", subs)
	}
	if hub.GetAgentInfo("missing") != nil {
		t.Fatal("missing agent should be nil")
	}
}

func TestHubProcessMessageAndAck(t *testing.T) {
	hub := NewAgentCommunicationHub(nil, 30, 30)
	wsA := newFakeWS()
	if err := hub.ConnectAgent("A", "sA", wsA); err != nil {
		t.Fatal(err)
	}

	// requires_ack triggers an acknowledge message back to the sender.
	hb := `{"id": "hb1", "type": "heartbeat", "from_agent": "A", "to_agents": [], "timestamp": "2024-01-02T03:04:05+00:00", "payload": {}, "requires_ack": true}`
	hub.ProcessMessage("A", hb)
	if v, _ := hub.Metrics.Get("messages_received"); v != 1 {
		t.Fatalf("messages_received = %v", v)
	}
	found := false
	for _, s := range wsA.sentText {
		if strings.Contains(s, `"type": "acknowledge"`) && strings.Contains(s, `"ack_message_id": "hb1"`) {
			found = true
		}
	}
	if !found {
		t.Fatalf("no ack sent: %v", wsA.sentText)
	}

	// Pending acks are cleared by an acknowledge message.
	if !hub.SendMessage("A", MessageTypeNotification, wsObj("x", 1), true, nil) {
		t.Fatal("send failed")
	}
	if len(hub.PendingAcks) != 1 {
		t.Fatalf("pending = %d", len(hub.PendingAcks))
	}
	var pendingID string
	for id := range hub.PendingAcks {
		pendingID = id
	}
	ack := `{"id": "ack1", "type": "acknowledge", "from_agent": "A", "to_agents": [], "timestamp": "2024-01-02T03:04:05+00:00", "payload": {"ack_message_id": "` + pendingID + `"}}`
	hub.ProcessMessage("A", ack)
	if len(hub.PendingAcks) != 0 {
		t.Fatalf("pending after ack = %d", len(hub.PendingAcks))
	}
}

func TestHubStatusUpdateUsesTracker(t *testing.T) {
	tracker := &fakeTracker{}
	hub := NewAgentCommunicationHub(tracker, 30, 30)
	wsA, wsB := newFakeWS(), newFakeWS()
	_ = hub.ConnectAgent("A", "sA", wsA)
	_ = hub.ConnectAgent("B", "sB", wsB)
	_ = hub.SubscribeToChannel("B", "status")

	update := `{"id": "u1", "type": "status_update", "from_agent": "A", "to_agents": [], "timestamp": "2024-01-02T03:04:05+00:00", "payload": {"status": "busy", "current_task_id": "t1"}}`
	hub.ProcessMessage("A", update)
	if tracker.calls != 1 || tracker.status != "busy" {
		t.Fatalf("tracker = %+v", tracker)
	}
	if len(wsB.sentText) != 3 { // welcome + channel_subscribed + status update
		t.Fatalf("B messages = %d", len(wsB.sentText))
	}
	if !strings.Contains(wsB.sentText[2], `"agent_id": "A"`) {
		t.Fatalf("status broadcast = %s", wsB.sentText[2])
	}
}

func TestSubscriptionMatches(t *testing.T) {
	event := NewContextEvent(EventTypeUpdated, "branch", "ctx1", "u1", nil, wsObj("project_id", "p1", "git_branch_id", "b1"))

	global := &Subscription{Scope: SubscriptionScopeGlobal, Filters: entities.NewOrderedMap[any]()}
	if !global.Matches(event) {
		t.Fatal("global should match")
	}
	user := &Subscription{Scope: SubscriptionScopeUser, Filters: wsObj("user_id", "u1")}
	if !user.Matches(event) {
		t.Fatal("user should match")
	}
	wrongUser := &Subscription{Scope: SubscriptionScopeUser, Filters: wsObj("user_id", "u2")}
	if wrongUser.Matches(event) {
		t.Fatal("wrong user should not match")
	}
	project := &Subscription{Scope: SubscriptionScopeProject, Filters: wsObj("project_id", "p1")}
	if !project.Matches(event) {
		t.Fatal("project should match")
	}
	branch := &Subscription{Scope: SubscriptionScopeBranch, Filters: wsObj("git_branch_id", "b1")}
	if !branch.Matches(event) {
		t.Fatal("branch should match")
	}
	task := &Subscription{Scope: SubscriptionScopeTask, Filters: wsObj("task_id", "ctx1")}
	if !task.Matches(event) {
		t.Fatal("task should match")
	}
	// String event_types filters never match the enum, like Python.
	byType := &Subscription{Scope: SubscriptionScopeGlobal, Filters: wsObj("event_types", []any{"context.updated"})}
	if byType.Matches(event) {
		t.Fatal("string event_types filter should not match")
	}
	byEnum := &Subscription{Scope: SubscriptionScopeGlobal, Filters: wsObj("event_types", []any{EventTypeUpdated})}
	if !byEnum.Matches(event) {
		t.Fatal("enum event_types filter should match")
	}
	byLevel := &Subscription{Scope: SubscriptionScopeGlobal, Filters: wsObj("levels", []any{"branch"})}
	if !byLevel.Matches(event) {
		t.Fatal("level filter should match")
	}
}

func TestContextNotificationService(t *testing.T) {
	service := NewContextNotificationService()
	ws := newFakeWS()
	ws.Accept()
	sub := service.Subscribe(ws, "c1", SubscriptionScopeGlobal, nil)
	if sub.ClientID != "c1" {
		t.Fatalf("sub = %+v", sub)
	}
	if len(ws.sentJSON) != 1 {
		t.Fatalf("welcome = %d", len(ws.sentJSON))
	}

	service.BroadcastEvent(NewContextEvent(EventTypeCreated, "global", "ctx1", "u1", nil, nil))
	if len(ws.sentJSON) != 2 {
		t.Fatalf("broadcast = %d", len(ws.sentJSON))
	}
	if v, _ := service.Stats.Get("events_sent"); v != 1 {
		t.Fatalf("events_sent = %v", v)
	}

	// A disconnected websocket is unsubscribed.
	ws.state = WebSocketStateDisconnected
	service.BroadcastEvent(NewContextEvent(EventTypeCreated, "global", "ctx1", "u1", nil, nil))
	if service.Subscriptions.Len() != 0 {
		t.Fatalf("subscriptions = %d", service.Subscriptions.Len())
	}

	// Notify queues an event and Start processes it.
	ws2 := newFakeWS()
	ws2.Accept()
	service.Subscribe(ws2, "c2", SubscriptionScopeGlobal, nil)
	service.Notify(EventTypeUpdated, "global", "ctx2", "u1", nil, nil)
	if v, _ := service.Stats.Get("events_queued"); v != 1 {
		t.Fatalf("events_queued = %v", v)
	}
	service.Start()
	deadline := time.Now().Add(3 * time.Second)
	for ws2.jsonCount() < 2 {
		if time.Now().After(deadline) {
			t.Fatalf("event not processed: %d messages", ws2.jsonCount())
		}
		time.Sleep(5 * time.Millisecond)
	}
	service.Stop()

	stats := service.GetStats()
	if strings.Join(stats.Keys(), ",") != "events_sent,events_queued,active_connections,total_connections,errors,queue_size,subscriptions" {
		t.Fatalf("stats keys = %v", stats.Keys())
	}
}

func TestWebSocketManagerHandleMessage(t *testing.T) {
	service := NewContextNotificationService()
	manager := NewWebSocketManager(service)
	ws := newFakeWS()
	if err := manager.Connect(ws, "c1"); err != nil {
		t.Fatal(err)
	}
	if manager.NotificationService.Subscriptions.Len() != 1 {
		t.Fatal("connect did not subscribe")
	}

	if err := manager.HandleMessage(ws, "c1", wsObj("type", "ping")); err != nil {
		t.Fatal(err)
	}
	if err := manager.HandleMessage(ws, "c1", wsObj("type", "get_stats")); err != nil {
		t.Fatal(err)
	}
	if err := manager.HandleMessage(ws, "c1", wsObj("type", "subscribe", "scope", "task", "filters", wsObj("task_id", "t1"))); err != nil {
		t.Fatal(err)
	}
	if err := manager.HandleMessage(ws, "c1", wsObj("type", "weird")); err != nil {
		t.Fatal(err)
	}
	if err := manager.HandleMessage(ws, "c1", wsObj("type", "subscribe", "scope", "bogus")); err == nil {
		t.Fatal("bogus scope should fail")
	}

	types := []string{}
	for _, d := range ws.sentJSON {
		m := d.(*entities.OrderedMap[any])
		v, _ := m.Get("type")
		types = append(types, v.(string))
	}
	if strings.Join(types, ",") != "welcome,pong,stats,welcome,subscribed,error" {
		t.Fatalf("types = %v", types)
	}

	manager.Disconnect(ws, "c1")
	if manager.NotificationService.Subscriptions.Len() != 0 {
		t.Fatal("disconnect did not unsubscribe")
	}
}
