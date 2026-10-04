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
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
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

func (e *streamEnv) sessionList(t *testing.T, user string) []map[string]any {
	t.Helper()
	status, body := e.restGet(t, user, "/api/v2/sessions")
	if status != 200 {
		t.Fatalf("list sessions = %d %v", status, body)
	}
	var out []map[string]any
	for _, row := range body.([]any) {
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
		return len(body.([]any))
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
	events := body.([]any)
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
