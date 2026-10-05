package httpapp

import (
	"bufio"
	"context"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"agenthub/fastmcp/auth/domain/services"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// wsTestToken mints a local JWT the unified validator accepts, with the given scopes.
func wsTestToken(t *testing.T, scopes []string) string {
	t.Helper()
	return wsTestTokenFor(t, "user-1", scopes)
}

// wsTestTokenFor is wsTestToken for a chosen user id.
func wsTestTokenFor(t *testing.T, user string, scopes []string) string {
	t.Helper()
	secret := "ws-mount-test-secret-000000000000"
	t.Setenv("JWT_SECRET_KEY", secret)
	t.Setenv("AUTH_PROVIDER", "keycloak")
	t.Setenv("KEYCLOAK_URL", "")
	svc, err := services.NewJWTService(secret, services.DefaultIssuer)
	if err != nil {
		t.Fatalf("NewJWTService: %v", err)
	}
	token, err := svc.GenerateToken(user, scopes, 1, "tid-1", services.DefaultAudience)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	return token
}

// wsTestDial performs the client half of the RFC 6455 handshake.
func wsTestDial(t *testing.T, serverURL, path string) (net.Conn, *bufio.Reader) {
	t.Helper()
	u, err := url.Parse(serverURL)
	if err != nil {
		t.Fatalf("parse server url: %v", err)
	}
	conn, err := net.Dial("tcp", u.Host)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	key := base64.StdEncoding.EncodeToString([]byte("0123456789abcdef"))
	req := "GET " + path + " HTTP/1.1\r\nHost: " + u.Host +
		"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
		"\r\nSec-WebSocket-Version: 13\r\n\r\n"
	if _, err := conn.Write([]byte(req)); err != nil {
		_ = conn.Close()
		t.Fatalf("write handshake: %v", err)
	}
	br := bufio.NewReader(conn)
	resp, err := http.ReadResponse(br, nil)
	if err != nil {
		_ = conn.Close()
		t.Fatalf("read handshake: %v", err)
	}
	if resp.StatusCode != http.StatusSwitchingProtocols {
		_ = conn.Close()
		t.Fatalf("handshake status = %d, want 101", resp.StatusCode)
	}
	return conn, br
}

// wsTestDialStatus performs the handshake and returns the HTTP status when the
// server refuses the upgrade.
func wsTestDialStatus(t *testing.T, serverURL, path string) int {
	t.Helper()
	u, err := url.Parse(serverURL)
	if err != nil {
		t.Fatalf("parse server url: %v", err)
	}
	conn, err := net.Dial("tcp", u.Host)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()
	key := base64.StdEncoding.EncodeToString([]byte("0123456789abcdef"))
	req := "GET " + path + " HTTP/1.1\r\nHost: " + u.Host +
		"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
		"\r\nSec-WebSocket-Version: 13\r\n\r\n"
	if _, err := conn.Write([]byte(req)); err != nil {
		t.Fatalf("write handshake: %v", err)
	}
	resp, err := http.ReadResponse(bufio.NewReader(conn), nil)
	if err != nil {
		t.Fatalf("read handshake: %v", err)
	}
	return resp.StatusCode
}

// wsTestReadFrame reads one unmasked server frame.
func wsTestReadFrame(t *testing.T, br *bufio.Reader) (byte, []byte) {
	t.Helper()
	header := make([]byte, 2)
	if _, err := io.ReadFull(br, header); err != nil {
		t.Fatalf("read frame header: %v", err)
	}
	opcode := header[0] & 0x0f
	if header[1]&0x80 != 0 {
		t.Fatal("server frame must not be masked")
	}
	length := int64(header[1] & 0x7f)
	switch length {
	case 126:
		ext := make([]byte, 2)
		if _, err := io.ReadFull(br, ext); err != nil {
			t.Fatalf("read frame length: %v", err)
		}
		length = int64(binary.BigEndian.Uint16(ext))
	case 127:
		ext := make([]byte, 8)
		if _, err := io.ReadFull(br, ext); err != nil {
			t.Fatalf("read frame length: %v", err)
		}
		length = int64(binary.BigEndian.Uint64(ext))
	}
	payload := make([]byte, length)
	if _, err := io.ReadFull(br, payload); err != nil {
		t.Fatalf("read frame payload: %v", err)
	}
	return opcode, payload
}

// wsTestWriteText writes one masked client text frame.
func wsTestWriteText(t *testing.T, conn net.Conn, payload []byte) {
	t.Helper()
	wsTestWriteFrame(t, conn, true, wsOpText, payload)
}

// wsTestWriteFrame writes one masked client frame; fin false starts or continues a fragmented message.
func wsTestWriteFrame(t *testing.T, conn net.Conn, fin bool, opcode byte, payload []byte) {
	t.Helper()
	if err := wsTestTryWriteFrame(conn, fin, opcode, payload); err != nil {
		t.Fatalf("write frame: %v", err)
	}
}

// wsTestTryWriteFrame is wsTestWriteFrame for a server that may close the connection mid-write.
func wsTestTryWriteFrame(conn net.Conn, fin bool, opcode byte, payload []byte) error {
	mask := [4]byte{0x11, 0x22, 0x33, 0x44}
	first := opcode
	if fin {
		first |= 0x80
	}
	header := []byte{first}
	switch n := len(payload); {
	case n < 126:
		header = append(header, 0x80|byte(n))
	case n < 1<<16:
		header = append(header, 0x80|126, byte(n>>8), byte(n))
	default:
		header = append(header, 0x80|127)
		header = binary.BigEndian.AppendUint64(header, uint64(n))
	}
	header = append(header, mask[:]...)
	masked := make([]byte, len(payload))
	for i := range payload {
		masked[i] = payload[i] ^ mask[i%4]
	}
	_, err := conn.Write(append(header, masked...))
	return err
}

func wsTestJSON(t *testing.T, payload []byte) map[string]any {
	t.Helper()
	var out map[string]any
	if err := json.Unmarshal(payload, &out); err != nil {
		t.Fatalf("decode frame %q: %v", payload, err)
	}
	return out
}

func TestMountWebSocketsRealtimeConnect(t *testing.T) {
	token := wsTestToken(t, nil)
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(token))
	defer conn.Close()

	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("opcode = %d, want text", opcode)
	}
	msg := wsTestJSON(t, payload)
	if msg["type"] != "sync" {
		t.Fatalf("type = %v, want sync", msg["type"])
	}
	body, ok := msg["payload"].(map[string]any)
	if !ok {
		t.Fatalf("payload type = %T", msg["payload"])
	}
	if body["action"] != "welcome" {
		t.Fatalf("action = %v, want welcome", body["action"])
	}
	data, _ := body["data"].(map[string]any)
	primary, _ := data["primary"].(map[string]any)
	if primary["user_id"] != "user-1" {
		t.Fatalf("user_id = %v, want user-1", primary["user_id"])
	}
	if primary["authenticated"] != true {
		t.Fatalf("authenticated = %v, want true", primary["authenticated"])
	}

	// The defect this pins lived in the CALL SITE: the handler accepted the socket and never added
	// it to routes.connections, so every broadcast went nowhere and no test noticed. A frame
	// addressed to THIS connection's user must arrive on THIS socket.
	roomData := entities.NewOrderedMap[any]()
	roomData.Set("id", "dev/alice")
	roomData.Set("room", "dev")
	roomData.Set("seat_key", "alice")
	if err := routes.BroadcastDataChange(context.Background(), "created", "seat", "dev/alice", "user-1", roomData, nil); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}
	_ = conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	opcode, payload = wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("broadcast opcode = %d, want text", opcode)
	}
	broadcast := wsTestJSON(t, payload)
	if broadcast["type"] != "update" {
		t.Fatalf("broadcast type = %v, want update - the accepted socket was not registered", broadcast["type"])
	}
	body, _ = broadcast["payload"].(map[string]any)
	if body["entity"] != "seat" || body["action"] != "created" {
		t.Fatalf("broadcast payload = %v, want entity seat / action created", broadcast["payload"])
	}
}

func TestMountWebSocketsConnectorConnect(t *testing.T) {
	token := wsTestToken(t, []string{routes.SessionStreamWriteScope})
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDial(t, server.URL, "/ws/connector?token="+url.QueryEscape(token))
	defer conn.Close()

	wsTestWriteText(t, conn, []byte(`{"type":"hello","connector_id":"conn-1"}`))
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("opcode = %d, want text", opcode)
	}
	msg := wsTestJSON(t, payload)
	if msg["type"] != "ready" {
		t.Fatalf("type = %v, want ready", msg["type"])
	}
	if msg["connector_id"] != "conn-1" {
		t.Fatalf("connector_id = %v, want conn-1", msg["connector_id"])
	}
}

func TestMountWebSocketsConnectorRequiresScope(t *testing.T) {
	token := wsTestToken(t, nil)
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	status := wsTestDialStatus(t, server.URL, "/ws/connector?token="+url.QueryEscape(token))
	if status != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", status)
	}
}

func TestMountWebSocketsRealtimeRejectsMissingToken(t *testing.T) {
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	status := wsTestDialStatus(t, server.URL, "/ws/realtime")
	if status != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", status)
	}
}

func TestMountWebSocketsRealtimeWithCORSAndOrigin(t *testing.T) {
	token := wsTestToken(t, nil)
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(withCORS(mux))
	defer server.Close()

	u, err := url.Parse(server.URL)
	if err != nil {
		t.Fatal(err)
	}
	conn, err := net.Dial("tcp", u.Host)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	key := base64.StdEncoding.EncodeToString([]byte("0123456789abcdef"))
	req := "GET /ws/realtime?token=" + url.QueryEscape(token) + " HTTP/1.1\r\nHost: " + u.Host +
		"\r\nOrigin: https://4genthub.com\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
		"\r\nSec-WebSocket-Version: 13\r\n\r\n"
	if _, err := conn.Write([]byte(req)); err != nil {
		t.Fatal(err)
	}
	br := bufio.NewReader(conn)
	resp, err := http.ReadResponse(br, nil)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusSwitchingProtocols {
		t.Fatalf("handshake status = %d, want 101", resp.StatusCode)
	}
}
