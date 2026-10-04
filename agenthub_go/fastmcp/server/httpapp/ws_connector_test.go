package httpapp

// Handler tests for the session stream: the connector ingest socket, the owner's viewer
// socket and the two REST routes, driven through a real websocket client. They port
// agenthub_main/src/tests/session_stream/session_stream_test.py. Tests that touch the
// database run on the Postgres named by AGENTHUB_TEST_PG_URL (recipe in
// session_stream/testdb); without it they skip. The tests that never reach the database
// run everywhere.

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/auth"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// streamEnv is the stream endpoints of one App on one server.
type streamEnv struct {
	server   *httptest.Server
	sessions *database.SessionManager
}

// newStreamEnv serves the stream routes over sessions (nil for tests that never read the database).
func newStreamEnv(t *testing.T, sessions *database.SessionManager) *streamEnv {
	t.Helper()
	// The REST routes validate the bearer token as NewApp wires it: the real local-JWT path.
	prev := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = auth.GetCurrentUserUniversal
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = prev })
	mux := http.NewServeMux()
	(&App{Sessions: sessions}).registerSessionStreamRoutes(mux)
	mountWebSockets(mux, sessions)
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	return &streamEnv{server: server, sessions: sessions}
}

func newPGStreamEnv(t *testing.T) *streamEnv {
	t.Helper()
	return newStreamEnv(t, testdb.NewSessions(t))
}

// streamConn is one client websocket whose reads fail after 5s instead of hanging.
type streamConn struct {
	t    *testing.T
	conn net.Conn
	br   *bufio.Reader
}

func (e *streamEnv) dial(t *testing.T, path, token string) *streamConn {
	t.Helper()
	conn, br := wsTestDial(t, e.server.URL, path+"?token="+url.QueryEscape(token))
	t.Cleanup(func() { _ = conn.Close() })
	_ = conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	return &streamConn{t: t, conn: conn, br: br}
}

func (e *streamEnv) connector(t *testing.T, user string) *streamConn {
	t.Helper()
	return e.dial(t, "/ws/connector", wsTestTokenFor(t, user, []string{routes.SessionStreamWriteScope}))
}

func (e *streamEnv) viewer(t *testing.T, user, sessionID string) *streamConn {
	t.Helper()
	return e.dial(t, "/ws/sessions/"+sessionID, wsTestTokenFor(t, user, nil))
}

func (c *streamConn) sendRaw(raw string) {
	c.t.Helper()
	wsTestWriteText(c.t, c.conn, []byte(raw))
}

func (c *streamConn) send(v any) {
	c.t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		c.t.Fatal(err)
	}
	c.sendRaw(string(b))
}

// recv reads one text frame as a JSON object.
func (c *streamConn) recv() map[string]any {
	c.t.Helper()
	opcode, payload := wsTestReadFrame(c.t, c.br)
	if opcode != wsOpText {
		c.t.Fatalf("opcode = %d (payload %q), want a text frame", opcode, payload)
	}
	return wsTestJSON(c.t, payload)
}

// recvClose reads the close frame the server sends.
func (c *streamConn) recvClose() (int, string) {
	c.t.Helper()
	return readClose(c.t, c.br)
}

// hello performs the hello/ready exchange.
func (c *streamConn) hello(connectorID string) {
	c.t.Helper()
	c.send(map[string]any{"type": "hello", "connector_id": connectorID})
	if got := c.recv(); got["type"] != "ready" || got["connector_id"] != connectorID {
		c.t.Fatalf("hello answered %v", got)
	}
}

// register sends a session message and returns the session id from the session_ack.
func (c *streamConn) register(key string) string {
	c.t.Helper()
	c.send(map[string]any{"type": "session", "session_key": key, "name": "coder"})
	ack := c.recv()
	if ack["type"] != "session_ack" {
		c.t.Fatalf("session answered %v", ack)
	}
	return ack["session_id"].(string)
}

// ingest is hello + register on a fresh connector socket.
func (c *streamConn) ingest(key string) string {
	c.t.Helper()
	c.hello("c1")
	return c.register(key)
}

func (c *streamConn) appendEvents(key string, events ...any) map[string]any {
	c.t.Helper()
	c.send(map[string]any{"type": "events", "session_key": key, "events": events})
	return c.recv()
}

func event(payload any) map[string]any {
	return map[string]any{"type": "message", "payload": payload}
}

// restGet is GET path with a bearer token; it returns the status and the decoded body.
func (e *streamEnv) restGet(t *testing.T, user, path string) (int, any) {
	t.Helper()
	req, err := http.NewRequest("GET", e.server.URL+path, nil)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Authorization", "Bearer "+wsTestTokenFor(t, user, nil))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var out any
	if err := json.Unmarshal(body, &out); err != nil {
		t.Fatalf("GET %s: body %q: %v", path, body, err)
	}
	return resp.StatusCode, out
}

// wrapped is the list under key of a Python-shaped body {key: [...]}.
func wrapped(t *testing.T, body any, key string) []any {
	t.Helper()
	obj, ok := body.(map[string]any)
	if !ok || len(obj) != 1 {
		t.Fatalf("body is a %T, want an object with only %q", body, key)
	}
	list, ok := obj[key].([]any)
	if !ok {
		t.Fatalf("body %v has no list under %q", obj, key)
	}
	return list
}

func (e *streamEnv) sessionList(t *testing.T, user string) []map[string]any {
	t.Helper()
	status, body := e.restGet(t, user, "/api/v2/sessions")
	if status != 200 {
		t.Fatalf("list sessions = %d %v", status, body)
	}
	var out []map[string]any
	for _, row := range wrapped(t, body, "sessions") {
		out = append(out, row.(map[string]any))
	}
	return out
}

func (e *streamEnv) sessionStatus(t *testing.T, user, sessionID string) string {
	t.Helper()
	for _, row := range e.sessionList(t, user) {
		if row["id"] == sessionID {
			return row["status"].(string)
		}
	}
	t.Fatalf("session %s not in %s's list", sessionID, user)
	return ""
}

func (e *streamEnv) waitStatus(t *testing.T, user, sessionID, want string) {
	t.Helper()
	waitFor(t, "session status "+want, func() bool { return e.sessionStatus(t, user, sessionID) == want })
}

func TestSessionEventsLimitIsClampedTo1000(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	sid := c.ingest("s1")
	batch := make([]any, session_stream.MaxEventsPerBatch)
	for i := range batch {
		batch[i] = map[string]any{}
	}
	for i := 1; i <= 6; i++ {
		if got := c.appendEvents("s1", batch...); got["last_seq"] != float64(200*i) {
			t.Fatalf("batch %d: %v", i, got)
		}
	}
	count := func(query string) int {
		status, body := env.restGet(t, "user-1", "/api/v2/sessions/"+sid+"/events"+query)
		if status != 200 {
			t.Fatalf("events%s = %d %v", query, status, body)
		}
		return len(wrapped(t, body, "events"))
	}
	if got := count("?limit=5000"); got != 1000 {
		t.Fatalf("limit=5000 returned %d events, want 1000", got)
	}
	if got := count("?after_seq=1150&limit=5000"); got != 50 {
		t.Fatalf("after_seq=1150 returned %d events, want 50", got)
	}
	if got := count("?limit=7"); got != 7 {
		t.Fatalf("limit=7 returned %d events", got)
	}
}

func TestUserBCannotListReadReplayOrAppendToUserAsSession(t *testing.T) {
	env := newPGStreamEnv(t)
	a := env.connector(t, "user-a")
	sidA := a.ingest("s1")
	a.appendEvents("s1", event(map[string]any{"text": "secret"}))

	// list
	if rows := env.sessionList(t, "user-b"); len(rows) != 0 {
		t.Fatalf("user B lists %v", rows)
	}
	// read (REST events)
	if status, body := env.restGet(t, "user-b", "/api/v2/sessions/"+sidA+"/events"); status != http.StatusNotFound {
		t.Fatalf("user B reads user A's events: %d %v, want 404", status, body)
	}
	// replay (viewer socket)
	if code, _ := env.viewer(t, "user-b", sidA).recvClose(); code != routes.SessionStreamNotFoundCode {
		t.Fatalf("user B's viewer closed %d, want 4004", code)
	}
	// append: B reuses A's connector id and session key and gets its own session
	b := env.connector(t, "user-b")
	sidB := b.ingest("s1")
	if sidB == sidA {
		t.Fatal("user B resolved to user A's session id")
	}
	b.appendEvents("s1", event(map[string]any{"text": "from b"}))
	status, body := env.restGet(t, "user-a", "/api/v2/sessions/"+sidA+"/events")
	events := wrapped(t, body, "events")
	if status != 200 || len(events) != 1 || events[0].(map[string]any)["payload"].(map[string]any)["text"] != "secret" {
		t.Fatalf("user A's events changed: %d %v", status, body)
	}
	// and the repository itself refuses B an append to A's session
	if _, err := session_stream.AppendEvents(context.Background(), env.sessions, "user-b", sidA, []any{entities.NewOrderedMap[any]()}); err == nil ||
		err.Error() != "unknown session" {
		t.Fatalf("repository append for another user: %v", err)
	}
}

func TestSessionEventsOfAnUnknownSessionIs404(t *testing.T) {
	env := newPGStreamEnv(t)
	if status, body := env.restGet(t, "user-1", "/api/v2/sessions/does-not-exist/events"); status != http.StatusNotFound {
		t.Fatalf("status = %d %v, want 404", status, body)
	}
}

// Python's events route defaults to limit=500.
func TestSessionEventsDefaultLimitIs500(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	sid := c.ingest("s1")
	batch := make([]any, session_stream.MaxEventsPerBatch)
	for i := range batch {
		batch[i] = map[string]any{}
	}
	for i := 0; i < 3; i++ { // 600 events
		c.appendEvents("s1", batch...)
	}
	_, body := env.restGet(t, "user-1", "/api/v2/sessions/"+sid+"/events")
	if got := len(wrapped(t, body, "events")); got != 500 {
		t.Fatalf("no limit returned %d events, want 500", got)
	}
}

// Python answers {"sessions": [...]} and {"events": [...]}, also when empty.
func TestSessionRoutesAnswerAnObjectEvenWhenEmpty(t *testing.T) {
	env := newPGStreamEnv(t)
	if _, body := env.restGet(t, "user-1", "/api/v2/sessions"); fmt.Sprint(wrapped(t, body, "sessions")) != "[]" {
		t.Fatalf("empty list = %v", body)
	}
	sid := env.connector(t, "user-1").ingest("s1")
	if _, body := env.restGet(t, "user-1", "/api/v2/sessions/"+sid+"/events"); fmt.Sprint(wrapped(t, body, "events")) != "[]" {
		t.Fatalf("empty events = %v", body)
	}
}

// ---- the 1 MiB message cap counts characters, the read is bounded in bytes ----

// helloOfChars is a valid hello message of exactly chars characters; every pad character
// is the two-byte 'é' inside a string field.
func helloOfChars(chars int) string {
	const head, tail = `{"type":"hello","connector_id":"c1","pad":"`, `"}`
	return head + strings.Repeat("é", chars-len([]rune(head))-len(tail)) + tail
}

func TestConnectorCapCountsCharactersNotBytes(t *testing.T) {
	c := newStreamEnv(t, nil).connector(t, "user-1")

	atCap := helloOfChars(routes.SessionStreamMaxMsgChars)
	if len(atCap) <= routes.SessionStreamMaxMsgChars {
		t.Fatal("the probe must be larger in bytes than the cap")
	}
	c.sendRaw(atCap)
	if got := c.recv(); got["type"] != "ready" {
		t.Fatalf("a message of exactly 1 MiB characters (%d bytes) must be served, got %v", len(atCap), got)
	}
	c.sendRaw(helloOfChars(routes.SessionStreamMaxMsgChars + 1))
	if got := c.recv(); got["type"] != "error" || got["error"] != "message too large" {
		t.Fatalf("a message of 1 MiB + 1 characters must be refused, got %v", got)
	}
	c.hello("c1") // the socket is still usable
}

// connectionEnds reports whether the server closed the connection (a read ends in an error).
func (c *streamConn) connectionEnds() bool {
	_ = c.conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	_, err := io.Copy(io.Discard, c.br)
	var ne net.Error
	return err == nil || !(errors.As(err, &ne) && ne.Timeout())
}

func TestConnectorReadIsBoundedInBytes(t *testing.T) {
	over := make([]byte, wsMaxMessageBytes+1)
	for i := range over {
		over[i] = ' '
	}

	t.Run("one frame", func(t *testing.T) {
		c := newStreamEnv(t, nil).connector(t, "user-1")
		_ = wsTestTryWriteFrame(c.conn, true, wsOpText, over) // the server may close before the last byte
		if !c.connectionEnds() {
			t.Fatal("a frame over the byte bound must end the connection")
		}
	})
	t.Run("fragments add up", func(t *testing.T) {
		c := newStreamEnv(t, nil).connector(t, "user-1")
		const piece = 1 << 20
		_ = wsTestTryWriteFrame(c.conn, false, wsOpText, over[:piece])
		for sent := piece; sent < len(over); sent += piece {
			end := min(sent+piece, len(over))
			if wsTestTryWriteFrame(c.conn, end == len(over), wsOpContinuation, over[sent:end]) != nil {
				break // closed by the server
			}
		}
		if !c.connectionEnds() {
			t.Fatal("fragments over the byte bound must end the connection")
		}
	})
}

// ---- the ingest flow, ported from the Python client tests ----

// Python: test_connector_rejects_bad_token_and_missing_scope. A real client sees the
// handshake refused (Python closes before accept, which the ASGI server turns into an
// HTTP 403 too); the missing-scope half is TestMountWebSocketsConnectorRequiresScope.
func TestConnectorRejectsABadToken(t *testing.T) {
	env := newStreamEnv(t, nil)
	if status := wsTestDialStatus(t, env.server.URL, "/ws/connector?token=nope"); status != http.StatusForbidden {
		t.Fatalf("handshake with a bad token = %d, want 403", status)
	}
}

// Python: test_events_for_unregistered_session_key_are_refused.
func TestConnectorRefusesEventsForAnUnregisteredSessionKey(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	c.hello("c1")
	if got := c.appendEvents("nope", event(map[string]any{"text": "x"})); got["type"] != "error" || got["error"] != "unknown session" {
		t.Fatalf("events for an unregistered key answered %v", got)
	}
}

// Python: test_hello_cannot_switch_connector_id.
func TestConnectorHelloCannotSwitchTheConnectorID(t *testing.T) {
	c := newStreamEnv(t, nil).connector(t, "user-1")
	c.hello("c1")
	c.send(map[string]any{"type": "hello", "connector_id": "c2"})
	if got := c.recv(); got["type"] != "error" || got["error"] != "connector_id already set" {
		t.Fatalf("the second hello answered %v", got)
	}
}

// Python: test_non_object_events_and_odd_project_do_not_crash_the_connector.
func TestConnectorSurvivesNonObjectEventsAndAnOddProject(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	c.hello("c1")
	c.send(map[string]any{"type": "session", "session_key": "s1", "name": "n", "project": map[string]any{"x": 1}})
	if got := c.recv(); got["type"] != "session_ack" {
		t.Fatalf("a session with a non-string project answered %v", got)
	}
	if got := c.appendEvents("s1", 1, "x", nil); got["type"] != "error" || got["error"] != "each event must be an object" {
		t.Fatalf("non-object events answered %v", got)
	}
	if got := c.appendEvents("s1", event(map[string]any{"a": 1})); got["type"] != "events_ack" {
		t.Fatalf("events after the error answered %v, want the socket to still work", got)
	}
}

// Python: test_disconnect_marks_sessions_offline.
func TestConnectorDisconnectMarksItsSessionsOffline(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	sid := c.ingest("s1")
	if got := env.sessionStatus(t, "user-1", sid); got != "active" {
		t.Fatalf("status before the disconnect = %q, want active", got)
	}
	_ = c.conn.Close()
	env.waitStatus(t, "user-1", sid, "offline")
}

// Python: test_reconnect_does_not_mark_live_sessions_offline. The longer-lived socket
// keeps the connector's sessions online; only the last socket to close takes them offline.
func TestConnectorReconnectKeepsTheLongerLivedSocketsSessionsOnline(t *testing.T) {
	env := newPGStreamEnv(t)
	older := env.connector(t, "user-1")
	sid := older.ingest("s1")
	newer := env.connector(t, "user-1")
	if got := newer.ingest("s1"); got != sid {
		t.Fatalf("the reconnect resolved %s, want %s", got, sid)
	}
	_ = newer.conn.Close()
	if got := env.sessionStatus(t, "user-1", sid); got != "active" {
		t.Fatalf("status after the newer socket closed = %q, want active", got)
	}
	_ = older.conn.Close()
	env.waitStatus(t, "user-1", sid, "offline")
}

// Python: list_sessions orders newest last_seen first; re-registering a key makes it newest.
func TestSessionListIsNewestLastSeenFirst(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	first := c.ingest("s1")
	second := c.register("s2")
	c.register("s1")
	rows := env.sessionList(t, "user-1")
	if len(rows) != 2 || rows[0]["id"] != first || rows[1]["id"] != second {
		t.Fatalf("list order = %v, want [%s %s]", rows, first, second)
	}
}

// The owner half of Python's test_ingest_then_owner_can_replay_but_other_user_cannot,
// through the real database: the in-memory viewer tests do not exercise this path.
func TestSessionViewerReplaysIngestedEventsFromTheDatabase(t *testing.T) {
	env := newPGStreamEnv(t)
	c := env.connector(t, "user-1")
	sid := c.ingest("s1")
	c.appendEvents("s1", event(map[string]any{"text": "hi"}))
	got := env.viewer(t, "user-1", sid).recv()
	if got["seq"] != float64(1) {
		t.Fatalf("viewer replayed seq %v, want 1", got["seq"])
	}
	if payload, ok := got["payload"].(map[string]any); !ok || payload["text"] != "hi" {
		t.Fatalf("viewer replayed payload %v, want {\"text\":\"hi\"}", got["payload"])
	}
}
