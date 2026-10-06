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

	"agenthub/fastmcp/auth"
	"agenthub/fastmcp/auth/domain/services"
	authinterface "agenthub/fastmcp/auth/interface"
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

// wsTestDialAuth is wsTestDial with one extra request header (e.g. Authorization), for the
// realtime socket's bearer path.
func wsTestDialAuth(t *testing.T, serverURL, path, header string) (net.Conn, *bufio.Reader) {
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
	extra := ""
	if header != "" {
		extra = "\r\n" + header
	}
	req := "GET " + path + " HTTP/1.1\r\nHost: " + u.Host +
		"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
		"\r\nSec-WebSocket-Version: 13" + extra + "\r\n\r\n"
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

// wsTestReadClose reads the server's close frame and returns its code and reason.
func wsTestReadClose(t *testing.T, br *bufio.Reader) (int, string) {
	t.Helper()
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpClose {
		t.Fatalf("opcode = %d, want close", opcode)
	}
	if len(payload) < 2 {
		t.Fatalf("close payload = %d bytes, want at least the 2-byte code", len(payload))
	}
	return int(binary.BigEndian.Uint16(payload[:2])), string(payload[2:])
}

// wsTestWelcomePrimary decodes a realtime welcome frame and returns payload.data.primary.
func wsTestWelcomePrimary(t *testing.T, payload []byte) map[string]any {
	t.Helper()
	msg := wsTestJSON(t, payload)
	if msg["type"] != "sync" {
		t.Fatalf("type = %v, want sync", msg["type"])
	}
	body, ok := msg["payload"].(map[string]any)
	if !ok {
		t.Fatalf("payload type = %T", msg["payload"])
	}
	data, _ := body["data"].(map[string]any)
	primary, _ := data["primary"].(map[string]any)
	if primary == nil {
		t.Fatal("welcome frame has no payload.data.primary")
	}
	return primary
}

// wsWireRESTAuth performs the wiring NewApp does so the REST bearer dependency resolves in a
// unit test exactly as in the server.
func wsWireRESTAuth(t *testing.T) {
	t.Helper()
	prev := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = auth.GetCurrentUserUniversal
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = prev })
}

// wsRESTUser drives the REST bearer dependency every REST route reaches (http.go currentUser
// -> authinterface.GetCurrentUser -> auth.GetCurrentUserUniversal) and returns the HTTP status
// plus the resolved user id ("" when refused).
func wsRESTUser(t *testing.T, authorization string) (int, string) {
	t.Helper()
	wsWireRESTAuth(t)

	req := httptest.NewRequest(http.MethodGet, "/rest-probe", nil)
	if authorization != "" {
		req.Header.Set("Authorization", authorization)
	}
	rec := httptest.NewRecorder()
	user, ok := currentUser(rec, req)
	if !ok || user == nil || user.ID == nil {
		return rec.Code, ""
	}
	return rec.Code, *user.ID
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

// TestMountWebSocketsConnectorRequiresScope checks the SCOPE refusal now completes the
// handshake and closes with 1008 plus wsScopeMissingReason, not a pre-upgrade 403 that a
// browser sees as 1006 with no reason.
func TestMountWebSocketsConnectorRequiresScope(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("JWT_SECRET_KEY", "ws-mount-test-secret-000000000000")
	t.Setenv("KEYCLOAK_URL", "")
	token := wsTestToken(t, nil)
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDial(t, server.URL, "/ws/connector?token="+url.QueryEscape(token))
	defer conn.Close()
	code, reason := wsTestReadClose(t, br)
	if code != wsClosePolicyViolation {
		t.Fatalf("close code = %d, want %d", code, wsClosePolicyViolation)
	}
	if reason != wsScopeMissingReason {
		t.Fatalf("close reason = %q, want %q", reason, wsScopeMissingReason)
	}
}

// TestMountWebSocketsConnectorRefusalsReadDifferentReasons pins the reviewer's find on the
// connector: an AUTH refusal and a SCOPE refusal are told apart by their close REASON, not
// merely both being 1008. Authentication and authorization are different events for the
// caller - the auth refusal means "come back with a token at all", the scope refusal means
// "come back with a better token" and must NOT read as a credential failure.
func TestMountWebSocketsConnectorRefusalsReadDifferentReasons(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("JWT_SECRET_KEY", "ws-mount-test-secret-000000000000")
	t.Setenv("KEYCLOAK_URL", "")

	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	// Authentication: a bearer no provider minted.
	const crafted = "self-crafted-token-no-provider-minted"
	authConn, authBr := wsTestDialAuth(t, server.URL, "/ws/connector", "Authorization: Bearer "+crafted)
	defer authConn.Close()
	authCode, authReason := wsTestReadClose(t, authBr)
	if authCode != wsClosePolicyViolation {
		t.Fatalf("auth refusal close code = %d, want %d", authCode, wsClosePolicyViolation)
	}
	if authReason != wsAuthInvalidTokenReason {
		t.Fatalf("auth refusal reason = %q, want %q", authReason, wsAuthInvalidTokenReason)
	}

	// Authorization: a credential the server accepts but that lacks sessions:write.
	noScope := wsTestToken(t, nil)
	scopeConn, scopeBr := wsTestDial(t, server.URL, "/ws/connector?token="+url.QueryEscape(noScope))
	defer scopeConn.Close()
	scopeCode, scopeReason := wsTestReadClose(t, scopeBr)
	if scopeCode != wsClosePolicyViolation {
		t.Fatalf("scope refusal close code = %d, want %d", scopeCode, wsClosePolicyViolation)
	}
	if scopeReason != wsScopeMissingReason {
		t.Fatalf("scope refusal reason = %q, want %q", scopeReason, wsScopeMissingReason)
	}

	// Authentication with NO token at all is the third refusal.
	missingConn, missingBr := wsTestDial(t, server.URL, "/ws/connector")
	defer missingConn.Close()
	missingCode, missingReason := wsTestReadClose(t, missingBr)
	if missingCode != wsClosePolicyViolation || missingReason != wsAuthMissingTokenReason {
		t.Fatalf("missing-token refusal = (%d, %q), want (%d, %q)", missingCode, missingReason, wsClosePolicyViolation, wsAuthMissingTokenReason)
	}

	// Distinctness BY CONSTRUCTION, not by inspection: the three refusals must be PAIRWISE
	// different. Each value above already equals its own constant, so this block goes red the
	// moment two reason constants are unified - not only after a caller sees the wrong message.
	reasons := map[string]string{
		"auth invalid token": authReason,
		"missing token":      missingReason,
		"missing scope":      scopeReason,
	}
	for a, ra := range reasons {
		for b, rb := range reasons {
			if a >= b {
				continue
			}
			if ra == rb {
				t.Fatalf("refusals %q and %q share reason %q - the three must be pairwise different", a, b, ra)
			}
		}
	}
}

// TestMountWebSocketsConnectorAgreesWithRESTWhenAuthDisabled is the connector half of the
// ruling the realtime socket already pins: with AUTH_ENABLED=false ONE decision governs both
// surfaces, so a bearer no provider minted is accepted by the REST dependency AND by the
// connector as the SAME user. The connector reaches it through wsAuthenticateRealtime (the
// helper handleConnector calls), and it must not impose the sessions:write scope rule the
// shared decision never consulted.
func TestMountWebSocketsConnectorAgreesWithRESTWhenAuthDisabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("ENV", "dev")
	wsWireRESTAuth(t)
	const crafted = "self-crafted-token-no-provider-minted"

	status, restUserID := wsRESTUser(t, "Bearer "+crafted)
	if status != http.StatusOK || restUserID == "" {
		t.Fatalf("REST refused the self-crafted token: status=%d user=%q", status, restUserID)
	}

	result, reason := wsAuthenticateRealtime(context.Background(), crafted)
	if reason != "" || result.UserID == nil {
		t.Fatalf("connector decision refused the token REST accepted: reason=%q", reason)
	}
	if *result.UserID != restUserID {
		t.Fatalf("connector user_id = %q, REST user_id = %q - the surfaces applied different decisions", *result.UserID, restUserID)
	}

	// The socket is actually served, not refused for a scope the shared decision never read.
	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDialAuth(t, server.URL, "/ws/connector", "Authorization: Bearer "+crafted)
	defer conn.Close()
	wsTestWriteText(t, conn, []byte(`{"type":"hello","connector_id":"conn-1"}`))
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("opcode = %d, want text", opcode)
	}
	if msg := wsTestJSON(t, payload); msg["type"] != "ready" {
		t.Fatalf("connector answered %v, want ready", msg)
	}
}

// TestWebSocketRejectionReasonsFitControlFrame pins the RFC 6455 limit: a close frame's reason
// is a control-frame payload capped at 123 bytes after the 2-byte code. Every refusal reason
// must fit or the client sees a truncated or invalid close, so the limit is a contract on the
// reason strings rather than a coincidence of their wording.
func TestWebSocketRejectionReasonsFitControlFrame(t *testing.T) {
	const limit = 123
	reasons := map[string]string{
		"auth missing":  wsAuthMissingTokenReason,
		"auth invalid":  wsAuthInvalidTokenReason,
		"scope missing": wsScopeMissingReason,
	}
	for name, reason := range reasons {
		if len(reason) > limit {
			t.Fatalf("%s reason is %d bytes, over the %d-byte control-frame limit", name, len(reason), limit)
		}
	}
}

func TestMountWebSocketsRealtimeRejectsMissingToken(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")

	// REST's bearer dependency refuses a missing credential even with auth off
	// (http.go currentUser writes 403 before the provider runs), and the socket must agree.
	if status, _ := wsRESTUser(t, ""); status != http.StatusForbidden {
		t.Fatalf("REST status = %d, want 403 for a missing bearer", status)
	}

	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDial(t, server.URL, "/ws/realtime")
	defer conn.Close()
	code, reason := wsTestReadClose(t, br)
	if code != wsClosePolicyViolation {
		t.Fatalf("close code = %d, want %d", code, wsClosePolicyViolation)
	}
	if reason != wsAuthMissingTokenReason {
		t.Fatalf("close reason = %q, want %q - a refused upgrade must say what the server wanted", reason, wsAuthMissingTokenReason)
	}
}

// TestMountWebSocketsRealtimeAgreesWithRESTOnSelfCraftedTokenWhenAuthDisabled pins the ruling:
// with AUTH_ENABLED=false one decision governs both surfaces, so a bearer no provider minted is
// accepted by the REST dependency AND by the realtime socket, as the same user. Before the fix
// REST accepted it while the socket answered 403. ENV=dev reproduces the local stack, where the
// REST dependency resolves its development fallback user.
func TestMountWebSocketsRealtimeAgreesWithRESTOnSelfCraftedTokenWhenAuthDisabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("ENV", "dev")
	wsWireRESTAuth(t)
	const crafted = "self-crafted-token-no-provider-minted"

	status, restUserID := wsRESTUser(t, "Bearer "+crafted)
	if status != http.StatusOK || restUserID == "" {
		t.Fatalf("REST refused the self-crafted token: status=%d user=%q", status, restUserID)
	}

	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDialAuth(t, server.URL, "/ws/realtime", "Authorization: Bearer "+crafted)
	defer conn.Close()

	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("opcode = %d, want text", opcode)
	}
	primary := wsTestWelcomePrimary(t, payload)
	if primary["user_id"] != restUserID {
		t.Fatalf("socket user_id = %v, REST user_id = %q - the surfaces applied different decisions", primary["user_id"], restUserID)
	}
	if primary["authenticated"] != true {
		t.Fatalf("authenticated = %v, want true", primary["authenticated"])
	}
}

// TestMountWebSocketsRealtimeAcceptsMintedTokenWithAuthEnabled is the other half of the same
// decision: with auth on a real minted token still upgrades the socket and REST still accepts.
func TestMountWebSocketsRealtimeAcceptsMintedTokenWithAuthEnabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	const user = "user-realtime-rest"
	token := wsTestTokenFor(t, user, nil)

	status, restUserID := wsRESTUser(t, "Bearer "+token)
	if status != http.StatusOK || restUserID != user {
		t.Fatalf("REST rejected the minted token: status=%d user=%q, want 200/%q", status, restUserID, user)
	}

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
	if got := wsTestWelcomePrimary(t, payload)["user_id"]; got != user {
		t.Fatalf("socket user_id = %v, want %q", got, user)
	}
}

// TestMountWebSocketsRealtimeRejectionCarriesReason checks a refused upgrade names what the
// server wanted instead of closing with 1006 and no message: the handshake is completed and
// closed with 1008 plus a readable reason, and REST refuses the same credential.
func TestMountWebSocketsRealtimeRejectionCarriesReason(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("JWT_SECRET_KEY", "ws-mount-test-secret-000000000000")
	t.Setenv("KEYCLOAK_URL", "")
	const crafted = "self-crafted-token-no-provider-minted"

	status, _ := wsRESTUser(t, "Bearer "+crafted)
	if status != http.StatusUnauthorized {
		t.Fatalf("REST status = %d, want 401 for the invalid token", status)
	}

	mux := http.NewServeMux()
	mountWebSockets(mux, nil)
	server := httptest.NewServer(mux)
	defer server.Close()

	conn, br := wsTestDialAuth(t, server.URL, "/ws/realtime", "Authorization: Bearer "+crafted)
	defer conn.Close()
	code, reason := wsTestReadClose(t, br)
	if code != wsClosePolicyViolation {
		t.Fatalf("close code = %d, want %d", code, wsClosePolicyViolation)
	}
	if reason != wsAuthInvalidTokenReason {
		t.Fatalf("close reason = %q, want %q - a refused upgrade must say what the server wanted", reason, wsAuthInvalidTokenReason)
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
