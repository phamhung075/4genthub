package httpapp

// The rigd phase-1 socket contract: the hello/ready handshake, ping/pong, the cursor that makes a
// resume after a lost ack exact, the safeguard frame and its alert, and the dead-man for rigd
// itself (ai_docs/core-architecture/rigd-boundaries.md 2.2, 2.3, 5 step 1, 7.3, 7.6).
//
// The cases that read the database run on the Postgres named by AGENTHUB_TEST_PG_URL (recipe in
// session_stream/testdb) and skip without it; the frame cases that never reach the database run
// everywhere. They live in their own file because the existing connector tests are the C4 port: this
// file is the phase-1 contract on top of it.

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	missedorm "agenthub/fastmcp/task_management/infrastructure/repositories/orm"
)

// rigdHello is the hello/ready exchange of a rigd connector: it advertises the capabilities it has
// and reads back what the server enabled.
func (c *streamConn) rigdHello(t *testing.T, connectorID string, capabilities ...string) {
	t.Helper()
	caps := make([]any, 0, len(capabilities))
	for _, name := range capabilities {
		caps = append(caps, name)
	}
	c.send(map[string]any{
		"type": "hello", "connector_id": connectorID, "protocol": 1,
		"client_version": "test", "capabilities": caps,
	})
	got := c.recv()
	if got["type"] != "ready" || got["connector_id"] != connectorID {
		t.Fatalf("hello answered %v", got)
	}
}

// pingBarrier sends a ping and waits for the pong. The safeguard frame carries NO ack by design
// (7.3: latest state wins, no seq, no cursor, no ack), so a following ping is what says the server
// has finished with the frame before the test reads the effect.
func (c *streamConn) pingBarrier(t *testing.T) {
	t.Helper()
	c.send(map[string]any{"type": "ping", "t": 1})
	if got := c.recv(); got["type"] != "pong" {
		t.Fatalf("ping answered %v, want pong", got)
	}
}

// safeguardFrame sends one safeguard frame and then the barrier.
func (c *streamConn) safeguardFrame(t *testing.T, frame map[string]any) {
	t.Helper()
	frame["type"] = "safeguard"
	c.send(frame)
	c.pingBarrier(t)
}

// wireSafeguardAlertStore assigns the real missed-notification store, which is where 7.3's alert
// lands for an offline user: BroadcastDataChange keeps it, and the next realtime connect replays it.
func wireSafeguardAlertStore(t *testing.T, sessions *database.SessionManager) {
	t.Helper()
	store, err := missedorm.NewMissedNotificationRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	prev := routes.MissedStore
	routes.MissedStore = store
	t.Cleanup(func() { routes.MissedStore = prev })
}

// storedAlert is one alert read back out of the notification store, exactly as the browser consumer
// would read it: the entity and the event_type from the frame, and the payload's primary.
type storedAlert struct {
	Entity    string
	EventType string
	EntityID  string
	Primary   *entities.OrderedMap[any]
}

func orderedChild(t *testing.T, m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	t.Helper()
	raw, _ := m.Get(key)
	child, ok := raw.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("%s = %v, want an object", key, raw)
	}
	return child
}

// storedAlerts reads every undelivered notification for user as one of 7.3's alerts.
func storedAlerts(t *testing.T, user string) []storedAlert {
	t.Helper()
	out := []storedAlert{}
	for _, n := range routes.FetchMissedNotifications(context.Background(), user, false, 100) {
		raw, _ := n.Get("message")
		message, ok := raw.(*entities.OrderedMap[any])
		if !ok {
			t.Fatalf("stored message = %v, want an object", raw)
		}
		payload := orderedChild(t, message, "payload")
		meta := orderedChild(t, message, "metadata")
		entity, _ := payload.Get("entity")
		eventType, _ := meta.Get("event_type")
		entityID, _ := meta.Get("entity_id")
		alert := storedAlert{Primary: orderedChild(t, orderedChild(t, payload, "data"), "primary")}
		alert.Entity, _ = entity.(string)
		alert.EventType, _ = eventType.(string)
		alert.EntityID, _ = entityID.(string)
		out = append(out, alert)
	}
	return out
}

func storedString(t *testing.T, m *entities.OrderedMap[any], key string) string {
	t.Helper()
	raw, _ := m.Get(key)
	s, _ := raw.(string)
	return s
}

// sessionEventCount is how many events the database holds for one session.
func sessionEventCount(t *testing.T, sessions *database.SessionManager, sessionID string) int {
	t.Helper()
	count := 0
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM agent_session_events WHERE session_id = $1`, sessionID).Scan(&count)
	}); err != nil {
		t.Fatal(err)
	}
	return count
}

// sessionCursor is the stored client cursor of one session.
func sessionCursor(t *testing.T, sessions *database.SessionManager, sessionID string) *string {
	t.Helper()
	var cursor *string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT client_cursor FROM agent_sessions WHERE id = $1`, sessionID).Scan(&cursor)
	}); err != nil {
		t.Fatal(err)
	}
	return cursor
}

// ---- the frame contract ----

// TestConnectorReadyReportsProtocolHeartbeatAndEchoedCapabilities: ready answers what the server
// will speak and what it enabled (2.2), a missing protocol means 1, and the server never echoes a
// capability it does not serve - which is what keeps a phase-2 frame off a phase-1 server (2.3.1).
func TestConnectorReadyReportsProtocolHeartbeatAndEchoedCapabilities(t *testing.T) {
	env := newStreamEnv(t, nil)

	c := env.connector(t, "user-rigd")
	c.send(map[string]any{
		"type": "hello", "connector_id": "rigd-1", "protocol": 1, "client_version": "0.1.0",
		"capabilities": []any{"ingest", "safeguards", "commands", "ledger"},
	})
	ready := c.recv()
	if ready["type"] != "ready" {
		t.Fatalf("hello answered %v", ready)
	}
	if ready["protocol"] != float64(connectorProtocolVersion) {
		t.Errorf("ready.protocol = %v, want %d", ready["protocol"], connectorProtocolVersion)
	}
	if ready["heartbeat_s"] != float64(connectorHeartbeatSeconds) {
		t.Errorf("ready.heartbeat_s = %v, want %d", ready["heartbeat_s"], connectorHeartbeatSeconds)
	}
	caps, ok := ready["capabilities"].([]any)
	if !ok || len(caps) != 2 || caps[0] != connectorCapabilityIngest || caps[1] != connectorCapabilitySafeguards {
		t.Errorf("ready.capabilities = %v, want [%s %s] (commands and ledger are not served here)",
			ready["capabilities"], connectorCapabilityIngest, connectorCapabilitySafeguards)
	}

	// A hello with no protocol at all means 1, and a client that advertises nothing is echoed
	// nothing rather than being handed capabilities it never named.
	bare := env.connector(t, "user-rigd")
	bare.send(map[string]any{"type": "hello", "connector_id": "rigd-2"})
	bareReady := bare.recv()
	if bareReady["protocol"] != float64(1) {
		t.Errorf("ready.protocol for a missing hello.protocol = %v, want 1", bareReady["protocol"])
	}
	if caps, ok := bareReady["capabilities"].([]any); !ok || len(caps) != 0 {
		t.Errorf("ready.capabilities for a bare hello = %v, want []", bareReady["capabilities"])
	}

	// A client speaking a version this server does not is answered the smaller one.
	ahead := env.connector(t, "user-rigd")
	ahead.send(map[string]any{"type": "hello", "connector_id": "rigd-3", "protocol": 7})
	if got := ahead.recv()["protocol"]; got != float64(connectorProtocolVersion) {
		t.Errorf("ready.protocol for hello.protocol=7 = %v, want %d", got, connectorProtocolVersion)
	}
}

// TestConnectorPingIsAnsweredWithPongAndAnUnknownTypeKeepsTheSocket: ping/pong is the heartbeat's
// whole client half (2.2), and an unknown type is answered with the ruled code and leaves the socket
// served (2.3.3) - the client logs it and continues.
func TestConnectorPingIsAnsweredWithPongAndAnUnknownTypeKeepsTheSocket(t *testing.T) {
	env := newStreamEnv(t, nil)
	c := env.connector(t, "user-rigd")
	c.hello("c1")

	c.send(map[string]any{"type": "ping", "t": 1712345678901})
	pong := c.recv()
	if pong["type"] != "pong" || pong["t"] != float64(1712345678901) {
		t.Fatalf("ping answered %v, want pong t=1712345678901", pong)
	}

	c.send(map[string]any{"type": "no_such_kind"})
	refused := c.recv()
	if refused["type"] != "error" || refused["error"] != "unknown type" {
		t.Fatalf("unknown type answered %v", refused)
	}
	if refused["code"] != "unknown_type" {
		t.Errorf("error.code = %v, want unknown_type", refused["code"])
	}
	if refused["fatal"] != false {
		t.Errorf("error.fatal = %v, want false (2.3.3 keeps the socket)", refused["fatal"])
	}

	// Still served: the refusal cost the connector that frame and nothing else.
	c.send(map[string]any{"type": "ping", "t": 2})
	if got := c.recv(); got["type"] != "pong" {
		t.Fatalf("after an unknown type the socket answered %v, want a pong", got)
	}
}

// TestConnectorRefusesASafeguardFrameWithoutTheEchoedCapability: the safeguard frame belongs to the
// `safeguards` capability (7.6), so a connector that did not advertise it - or a server that does not
// serve it - answers unknown_type and keeps the socket open (2.3).
func TestConnectorRefusesASafeguardFrameWithoutTheEchoedCapability(t *testing.T) {
	env := newStreamEnv(t, nil)
	c := env.connector(t, "user-rigd")
	c.rigdHello(t, "c1", connectorCapabilityIngest)

	c.send(map[string]any{
		"type": "safeguard", "rig": "rig-1", "safeguard": "compact",
		"state": "running", "restarts": 0, "age_s": 1,
	})
	refused := c.recv()
	if refused["type"] != "error" || refused["code"] != "unknown_type" || refused["fatal"] != false {
		t.Fatalf("safeguard without the capability answered %v", refused)
	}

	c.send(map[string]any{"type": "ping", "t": 1})
	if got := c.recv(); got["type"] != "pong" {
		t.Fatalf("the socket must stay open: %v", got)
	}
}

// TestConnectorClosesASocketSilentForThreeHeartbeats: 2.2's server half of the heartbeat. It is what
// makes the rigd dead-man timely on a machine that vanishes without closing its sockets.
func TestConnectorClosesASocketSilentForThreeHeartbeats(t *testing.T) {
	prev := wsConnectorIdleTimeout
	wsConnectorIdleTimeout = func() time.Duration { return 200 * time.Millisecond }
	t.Cleanup(func() { wsConnectorIdleTimeout = prev })

	env := newStreamEnv(t, nil)
	c := env.connector(t, "user-rigd")
	c.hello("c1")
	if !c.connectionEnds() {
		t.Fatal("a connector that sent no frame for three heartbeats must be closed by the server")
	}
}

// ---- the socket contract: a batch survives a lost ack (section 5 step 1's check) ----

// TestConnectorCursorSurvivesALostAckAndStoresTheBatchOnce is 5 step 1's stated check: send a batch,
// DROP the socket before reading the ack, reconnect, and receive session_ack.cursor equal to that
// batch's cursor with the event count stored exactly once.
//
// The drop is what makes it a check rather than a round trip: nothing on this side may confirm the
// batch, so the cursor can only be right if it committed WITH the events (2.1, option A).
func TestConnectorCursorSurvivesALostAckAndStoresTheBatchOnce(t *testing.T) {
	env := newPGStreamEnv(t)
	const user = "user-rigd"
	const key = "seat/lead"
	const cursor = "transcript:4096"

	first := env.connector(t, user)
	first.hello("c1")
	sid := first.register(key)

	batch := []any{
		event(map[string]any{"text": "one"}),
		event(map[string]any{"text": "two"}),
		event(map[string]any{"text": "three"}),
	}
	first.send(map[string]any{"type": "events", "session_key": key, "events": batch, "cursor": cursor})
	// The socket is dropped BEFORE the ack is read. The frame is already on the wire, the server
	// commits it and answers into a closed socket.
	_ = first.conn.Close()

	second := env.connector(t, user)
	second.hello("c1")

	// The reconnect asks for the session again, which is what a resuming connector does. The cursor
	// may not be stored the instant the second socket opens - the first socket's commit is still in
	// flight - so the frame is re-sent until it is, with a deadline that fails loudly. The deadline
	// is deliberately inside the socket's own read window, so the failure names the cursor rather
	// than surfacing as a read timeout.
	deadline := time.Now().Add(4 * time.Second)
	var ack map[string]any
	for {
		second.send(map[string]any{"type": "session", "session_key": key, "name": "coder"})
		_ = second.conn.SetReadDeadline(time.Now().Add(5 * time.Second))
		ack = second.recv()
		if ack["type"] != "session_ack" {
			t.Fatalf("session answered %v", ack)
		}
		if ack["cursor"] == cursor {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("session_ack.cursor = %v, want %q: the cursor did not commit with the batch", ack["cursor"], cursor)
		}
		time.Sleep(20 * time.Millisecond)
	}
	if ack["session_id"] != sid {
		t.Errorf("session_ack.session_id = %v, want %s", ack["session_id"], sid)
	}
	if ack["last_seq"] != float64(len(batch)) {
		t.Errorf("session_ack.last_seq = %v, want %d", ack["last_seq"], len(batch))
	}

	// EXACTLY ONCE: the batch was stored by the socket that never heard back.
	if got := sessionEventCount(t, env.sessions, sid); got != len(batch) {
		t.Fatalf("stored events = %d, want %d (the lost ack must not duplicate the batch)", got, len(batch))
	}
	if got := sessionCursor(t, env.sessions, sid); got == nil || *got != cursor {
		t.Fatalf("stored client_cursor = %v, want %q", got, cursor)
	}

	// events_ack carries the same value (2.2), so the stop-and-wait client advances its own cursor
	// from the ack it does receive.
	second.send(map[string]any{"type": "events", "session_key": key, "events": []any{event(map[string]any{"text": "four"})}, "cursor": "transcript:5120"})
	next := second.recv()
	if next["type"] != "events_ack" || next["cursor"] != "transcript:5120" {
		t.Fatalf("events_ack = %v, want cursor transcript:5120", next)
	}
	if next["last_seq"] != float64(len(batch)+1) {
		t.Errorf("events_ack.last_seq = %v, want %d", next["last_seq"], len(batch)+1)
	}
	if got := sessionEventCount(t, env.sessions, sid); got != len(batch)+1 {
		t.Fatalf("stored events = %d, want %d", got, len(batch)+1)
	}
}

// TestConnectorRefusesACursorOverItsByteBound: the cursor is opaque to the server and bounded at 512
// bytes (2.2), and the refusal is the store's own - the batch it belongs to is not stored either.
func TestConnectorRefusesACursorOverItsByteBound(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-rigd")
	c.hello("c1")
	sid := c.register("s1")

	c.send(map[string]any{
		"type": "events", "session_key": "s1", "events": []any{event(map[string]any{"text": "x"})},
		"cursor": string(make([]byte, 513)),
	})
	refused := c.recv()
	if refused["type"] != "error" || refused["error"] != "cursor is too long" {
		t.Fatalf("over-long cursor answered %v", refused)
	}
	if refused["code"] != "cursor_is_too_long" {
		t.Errorf("error.code = %v, want the stable code of the refusal", refused["code"])
	}
	if got := sessionEventCount(t, env.sessions, sid); got != 0 {
		t.Fatalf("stored events = %d, want 0: a refused batch stores nothing", got)
	}
}

// ---- 7.3: the server decides the alert ----

// TestSafeguardAlertRuleRaisesOnceAndAlertsAReconnect covers 7.3's rule end to end: the running ->
// stopped transition raises exactly one alert, a re-sent identical row raises NONE, a failure that
// happened while the connector was offline is alerted after the next ready, and restarts going up is
// the rule's other half.
func TestSafeguardAlertRuleRaisesOnceAndAlertsAReconnect(t *testing.T) {
	env := newPGStreamEnv(t)
	const user = "user-rigd"
	wireSafeguardAlertStore(t, env.sessions)

	row := func(state string, restarts int) map[string]any {
		return map[string]any{
			"rig": "rig-1", "safeguard": "compact", "state": state,
			"pid": 4242, "restarts": restarts, "age_s": 31, "at": time.Now().UnixMilli(),
		}
	}

	first := env.connector(t, user)
	first.rigdHello(t, "c1", connectorCapabilityIngest, connectorCapabilitySafeguards)

	// The first row for a key alerts nothing: there is no stored state it could have changed FROM.
	first.safeguardFrame(t, row("running", 0))
	if got := missedNotificationCount(t, env.sessions, user); got != 0 {
		t.Fatalf("alerts after the first running row = %d, want 0", got)
	}

	// The connector goes offline with running stored, and the next ready re-sends the rows.
	_ = first.conn.Close()
	second := env.connector(t, user)
	second.rigdHello(t, "c1", connectorCapabilityIngest, connectorCapabilitySafeguards)
	second.safeguardFrame(t, row("stopped", 0))

	alerts := storedAlerts(t, user)
	if len(alerts) != 1 {
		t.Fatalf("alerts after running -> stopped = %d, want exactly 1", len(alerts))
	}
	alert := alerts[0]
	if alert.EventType != safeguardAlertEventType || alert.Entity != rigSafeguardEntity {
		t.Fatalf("alert names event_type %q entity %q, want %q and %q",
			alert.EventType, alert.Entity, safeguardAlertEventType, rigSafeguardEntity)
	}
	if got := storedString(t, alert.Primary, "state"); got != "stopped" {
		t.Errorf("alert state = %q, want stopped", got)
	}
	if got := storedString(t, alert.Primary, "safeguard"); got != "compact" {
		t.Errorf("alert safeguard = %q, want compact", got)
	}
	if got := storedString(t, alert.Primary, "connector_id"); got != "c1" {
		t.Errorf("alert connector_id = %q, want c1", got)
	}

	// A re-sent identical row changes nothing, so it must not alert again.
	second.safeguardFrame(t, row("stopped", 0))
	if got := missedNotificationCount(t, env.sessions, user); got != 1 {
		t.Fatalf("alerts after re-sending the same row = %d, want 1 (no duplicate)", got)
	}

	// The rule's other half: restarts going up alerts even though the state is unchanged.
	second.safeguardFrame(t, row("stopped", 3))
	if got := missedNotificationCount(t, env.sessions, user); got != 2 {
		t.Fatalf("alerts after restarts went up = %d, want 2", got)
	}

	// Latest state wins: one row per key, holding the newest report.
	if got := sessionStateRowCount(t, env.sessions, user, "c1", "rig-1", "compact"); got != 1 {
		t.Fatalf("stored rig_safeguards rows for one key = %d, want 1 (the frame is an upsert)", got)
	}
}

// sessionStateRowCount is how many rig_safeguards rows one key holds.
func sessionStateRowCount(t *testing.T, sessions *database.SessionManager, userID, connectorID, rig, safeguard string) int {
	t.Helper()
	count := 0
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM rig_safeguards WHERE user_id = $1 AND connector_id = $2 AND rig = $3 AND safeguard = $4`,
			userID, connectorID, rig, safeguard).Scan(&count)
	}); err != nil {
		t.Fatal(err)
	}
	return count
}

// TestSafeguardFrameRefusesAStateOrSafeguardOutsideTheRuledSets: the two closed sets of 7.6 are
// stated to the database as CHECKs and refused here first, so a bad row never reaches a constraint.
func TestSafeguardFrameRefusesAStateOrSafeguardOutsideTheRuledSets(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-rigd")
	c.rigdHello(t, "c1", connectorCapabilityIngest, connectorCapabilitySafeguards)

	c.send(map[string]any{"type": "safeguard", "rig": "rig-1", "safeguard": "compact", "state": "paused", "restarts": 0, "age_s": 1})
	if got := c.recv(); got["type"] != "error" || got["error"] != "bad state" || got["code"] != "bad_state" {
		t.Fatalf("an unknown state answered %v", got)
	}
	c.send(map[string]any{"type": "safeguard", "rig": "rig-1", "safeguard": "keeper", "state": "running", "restarts": 0, "age_s": 1})
	if got := c.recv(); got["type"] != "error" || got["error"] != "bad safeguard" {
		t.Fatalf("an unknown safeguard answered %v", got)
	}
	c.send(map[string]any{"type": "safeguard", "rig": "", "safeguard": "compact", "state": "running", "restarts": 0, "age_s": 1})
	if got := c.recv(); got["type"] != "error" || got["error"] != "bad rig" {
		t.Fatalf("a missing rig answered %v", got)
	}
	if got := sessionStateRowCount(t, env.sessions, "user-rigd", "c1", "rig-1", "compact"); got != 0 {
		t.Fatalf("stored rows after three refused frames = %d, want 0", got)
	}
}

// TestRigdDeadmanAlertsWhenASafeguardsConnectorStaysOffline is 7.3's dead-man: a connector that
// advertised safeguards and stays offline past its heartbeat close is alerted for `rigd`, and a
// reconnect inside that window cancels it.
//
// The timer is the seam (wsConnectorDeadmanAfter), so the case drives the callback instead of
// waiting 75 seconds: what it checks is which delay was armed, and what firing it does.
func TestRigdDeadmanAlertsWhenASafeguardsConnectorStaysOffline(t *testing.T) {
	env := newPGStreamEnv(t)
	const user = "user-rigd"
	wireSafeguardAlertStore(t, env.sessions)

	type arm struct {
		delay time.Duration
		fire  func()
		timer *time.Timer
	}
	armed := make(chan arm, 4)
	prevAfter := wsConnectorDeadmanAfter
	wsConnectorDeadmanAfter = func(d time.Duration, f func()) *time.Timer {
		timer := time.AfterFunc(time.Hour, func() {})
		armed <- arm{delay: d, fire: f, timer: timer}
		return timer
	}
	t.Cleanup(func() { wsConnectorDeadmanAfter = prevAfter })

	first := env.connector(t, user)
	first.rigdHello(t, "c1", connectorCapabilityIngest, connectorCapabilitySafeguards)
	_ = first.conn.Close()

	var pending arm
	select {
	case pending = <-armed:
	case <-time.After(5 * time.Second):
		t.Fatal("closing the last socket of a safeguards connector must arm the rigd dead-man")
	}
	want := 3 * time.Duration(connectorHeartbeatSeconds) * time.Second
	if pending.delay != want {
		t.Fatalf("dead-man armed for %s, want %s (3 x heartbeat_s)", pending.delay, want)
	}

	pending.fire()
	alerts := storedAlerts(t, user)
	if len(alerts) != 1 {
		t.Fatalf("alerts after the heartbeat close = %d, want 1", len(alerts))
	}
	if got := storedString(t, alerts[0].Primary, "safeguard"); got != "rigd" {
		t.Errorf("dead-man alert safeguard = %q, want rigd", got)
	}
	if got := storedString(t, alerts[0].Primary, "connector_id"); got != "c1" {
		t.Errorf("dead-man alert connector_id = %q, want c1", got)
	}
	if alerts[0].EventType != safeguardAlertEventType || alerts[0].Entity != rigSafeguardEntity {
		t.Errorf("dead-man alert names event_type %q entity %q", alerts[0].EventType, alerts[0].Entity)
	}

	// A reconnect inside the heartbeat close cancels it, and the armed callback is inert: the
	// connector is back, so the silence it was armed for did not happen.
	second := env.connector(t, user)
	second.rigdHello(t, "c1", connectorCapabilityIngest, connectorCapabilitySafeguards)
	if pending.timer.Stop() {
		t.Error("the reconnect did not stop the pending dead-man")
	}
	pending.fire()
	if got := len(storedAlerts(t, user)); got != 1 {
		t.Fatalf("alerts after a reconnected callback fired = %d, want 1 (the connector is back)", got)
	}
}

// TestConnectorWithoutTheCapabilityIsNeverWatchedByTheDeadman: the dead-man is only for a connector
// that advertised safeguards, because it is the observer of rigd and rigd is the process that sends
// those rows. A one-shot ingest client must never be alerted for going away.
func TestConnectorWithoutTheCapabilityIsNeverWatchedByTheDeadman(t *testing.T) {
	prevAfter := wsConnectorDeadmanAfter
	armed := make(chan time.Duration, 4)
	wsConnectorDeadmanAfter = func(d time.Duration, f func()) *time.Timer {
		armed <- d
		return time.AfterFunc(time.Hour, func() {})
	}
	t.Cleanup(func() { wsConnectorDeadmanAfter = prevAfter })

	env := newStreamEnv(t, nil)
	c := env.connector(t, "user-rigd")
	c.rigdHello(t, "c1", connectorCapabilityIngest)
	_ = c.conn.Close()

	select {
	case d := <-armed:
		t.Fatalf("a connector without `safeguards` armed a dead-man for %s", d)
	case <-time.After(500 * time.Millisecond):
	}
}

// ---- 2.3a's column, written from session.state ----

// seatStateOf reads seat_state for one session out of GET /api/v2/sessions - the browser's single
// read path - and reports whether the key is on the row at all.
func seatStateOf(t *testing.T, env *streamEnv, user, sessionID string) (any, bool) {
	t.Helper()
	for _, row := range env.sessionList(t, user) {
		if row["id"] == sessionID {
			v, ok := row["seat_state"]
			return v, ok
		}
	}
	t.Fatalf("session %s is not in GET /api/v2/sessions", sessionID)
	return nil, false
}

// TestSessionStateReachesTheSessionListAndIsKeptWhenAbsent: session.state is written to
// agent_sessions.seat_state on every session frame (2.3a), the value arrives on the row the browser
// reads, a frame that carries no state keeps what an earlier one reported - the same rule an empty
// project follows - and a value outside the ruled two is refused without being stored.
func TestSessionStateReachesTheSessionListAndIsKeptWhenAbsent(t *testing.T) {
	env := newPGStreamEnv(t)
	const user = "user-rigd"
	c := env.connector(t, user)
	c.hello("c1")

	// send writes one session frame and returns whatever the server answered with: the test decides
	// which answers are acks and which are refusals.
	send := func(key string, extra map[string]any) map[string]any {
		frame := map[string]any{"type": "session", "session_key": key, "name": "coder"}
		for k, v := range extra {
			frame[k] = v
		}
		c.send(frame)
		return c.recv()
	}
	acked := func(t *testing.T, frame map[string]any) map[string]any {
		t.Helper()
		if frame["type"] != "session_ack" {
			t.Fatalf("session frame answered %v", frame)
		}
		return frame
	}

	ack := acked(t, send("s1", map[string]any{"state": "running"}))
	sid, _ := ack["session_id"].(string)
	if got, ok := seatStateOf(t, env, user, sid); !ok || got != "running" {
		t.Fatalf("seat_state after state=running = %v (present %v), want running", got, ok)
	}

	// A frame with no state does not erase what an earlier one reported.
	acked(t, send("s1", nil))
	if got, _ := seatStateOf(t, env, user, sid); got != "running" {
		t.Fatalf("seat_state after a frame with no state = %v, want running (kept)", got)
	}

	acked(t, send("s1", map[string]any{"state": "stopped"}))
	if got, _ := seatStateOf(t, env, user, sid); got != "stopped" {
		t.Fatalf("seat_state after state=stopped = %v, want stopped", got)
	}

	// session.source is a ruled frame field with no column and no server behaviour: the frame is
	// served and the field is not carried into the row.
	acked(t, send("s1", map[string]any{"source": "capture"}))
	if got, _ := seatStateOf(t, env, user, sid); got != "stopped" {
		t.Fatalf("seat_state after a source-only frame = %v, want stopped", got)
	}

	// The ruled set is running|stopped: anything else costs the connector that frame and stores
	// nothing, which is why the column needs no CHECK of its own.
	refused := send("s1", map[string]any{"state": "paused"})
	if refused["type"] != "error" || refused["error"] != "bad state" || refused["code"] != "bad_state" {
		t.Fatalf("state=paused answered %v", refused)
	}
	if got, _ := seatStateOf(t, env, user, sid); got != "stopped" {
		t.Fatalf("seat_state after a refused state = %v, want stopped (unchanged)", got)
	}

	// A session no connector has reported a state for carries the key with a null value: null and
	// absent are different answers to a client reading the field by name.
	c.send(map[string]any{"type": "session", "session_key": "s2", "name": "other"})
	other := c.recv()
	otherID, _ := other["session_id"].(string)
	if got, ok := seatStateOf(t, env, user, otherID); !ok || got != nil {
		t.Fatalf("seat_state for a session with no report = %v (present %v), want a null value", got, ok)
	}
}
