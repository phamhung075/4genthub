// ws_mount.go mounts the two WebSocket endpoints from the Python surface (B2):
// /ws/realtime (server/routes/websocket_routes.py) and /ws/connector
// (server/routes/session_stream_routes.py).
//
// server/routes/*.go ports only the framework-independent logic of those modules;
// the Starlette receive loops were left out, so the RFC 6455 upgrade, framing and
// the two receive loops live here. The shared notification helpers come from
// server/routes (websocket_routes.go) and the connector persistence comes from the
// session_stream package, so no business logic is duplicated.
package httpapp

import (
	"bufio"
	"context"
	"crypto/sha1"
	"encoding/base64"
	"encoding/binary"
	"fmt"
	"io"
	"math/rand"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	wslib "agenthub/fastmcp/websocket"
)

// RFC 6455 opcodes and handshake constants.
const (
	wsOpContinuation = 0x0
	wsOpText         = 0x1
	wsOpBinary       = 0x2
	wsOpClose        = 0x8
	wsOpPing         = 0x9
	wsOpPong         = 0xA

	// wsGUID is the RFC 6455 handshake magic string.
	wsGUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
	// wsClosePolicyViolation is the close code a rejected upgrade carries. The browser
	// WebSocket API exposes neither the HTTP status nor the body of a refused handshake, so a
	// bare 403 reaches the client as 1006 with no reason - indistinguishable from a network
	// drop. The upgrade is therefore completed and closed with this code and a reason the
	// client can read (WebSocketClient.ts handles 1008 as an authentication failure).
	wsClosePolicyViolation = 1008
	// wsMaxMessageBytes bounds one message (all its fragments together) so a bad client
	// cannot force an unbounded allocation. It is the most bytes the connector's limit of
	// SessionStreamMaxMsgChars characters can take (4 bytes per character in UTF-8); the
	// character limit itself is checked after the read.
	wsMaxMessageBytes = 4 * routes.SessionStreamMaxMsgChars
)

// mountWebSockets registers the realtime, connector and session viewer WebSocket endpoints. sessions
// is the connector's persistence manager; the realtime loop only needs the shared
// notification helpers in server/routes.
func mountWebSockets(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("GET /ws/realtime", handleRealtime)
	mux.HandleFunc("GET /ws/connector", handleConnector(sessions))
	mux.HandleFunc("GET /ws/sessions/{id}", handleSessionViewer(sessionStreamStore{sessions}))
}

// wsAuthMissingTokenReason / wsAuthInvalidTokenReason are what a rejected upgrade tells the
// client it wanted. A refused handshake's body never reaches a browser, so each reason stands
// alone: it names the credential and where the server reads it.
const (
	wsAuthMissingTokenReason = "Authentication required: pass a bearer token in the token query parameter or the Authorization header"
	wsAuthInvalidTokenReason = "Invalid or expired token: supply a valid Keycloak, API or MCP bearer token"
)

// wsScopeMissingReason is the connector's OTHER refusal: the credential was accepted but the
// token does not grant sessions:write. It is deliberately its own string, NOT one of the auth
// reasons above, because authentication and authorization are different events for the caller.
// An authentication refusal means "come back with a token at all"; this one means "come back
// with a better token". The authorization refusal is a LEGITIMATE outcome, not a credential
// failure, so it must not read as one: a client told its credential is bad discards a token
// that is actually fine. Collapsing both refusals into a single "rejected" reason is the
// natural result of treating "refused" as one case, and is exactly how a fix inherits the
// defect it was sent to close. Like the auth reasons it stays under the RFC 6455 123-byte
// control-frame limit (pinned by TestWebSocketRejectionReasonsFitControlFrame).
const wsScopeMissingReason = "Missing scope " + routes.SessionStreamWriteScope +
	": the credential is valid but this token must also grant session streaming"

// wsAuthenticateRealtime resolves the socket identity under the SAME decision the REST routes
// apply instead of giving the socket a rule of its own. Every REST route authenticates through
// http.go currentUser -> authinterface.GetCurrentUser, which with AUTH_ENABLED=false resolves
// the development identity for whatever bearer arrived without validating it (and, in the
// stack's dev environment, falls back to the development user when the provider cannot be
// consulted). This calls that same helper for the disabled case, so the two surfaces cannot
// drift; with auth on it keeps auth.ValidateTokenUniversal, which additionally accepts the
// generated MCP tokens the socket has always accepted.
//
// A non-empty second return is the reason the credential was refused.
func wsAuthenticateRealtime(ctx context.Context, token string) (auth.UnifiedAuthResult, string) {
	if token == "" {
		return auth.UnifiedAuthResult{}, wsAuthMissingTokenReason
	}
	if !auth.AuthEnabled() {
		user, err := authinterface.GetCurrentUser(ctx, &token, nil)
		if err != nil || user == nil || user.ID == nil || *user.ID == "" {
			return auth.UnifiedAuthResult{}, wsAuthInvalidTokenReason
		}
		email := user.Email
		return auth.UnifiedAuthResult{Valid: true, UserID: user.ID, Email: &email}, ""
	}
	result := auth.ValidateTokenUniversal(ctx, token, nil)
	if !result.Valid || result.UserID == nil || *result.UserID == "" {
		return auth.UnifiedAuthResult{}, wsAuthInvalidTokenReason
	}
	return result, ""
}

// wsRejectUpgrade refuses an upgrade by completing the handshake and immediately closing with
// wsClosePolicyViolation and reason. Completing the handshake first is deliberate: a plain 403
// reaches a browser as close code 1006 with no reason, so the client cannot tell a rejected
// credential from a network drop. Nothing is registered or served in between.
func wsRejectUpgrade(w http.ResponseWriter, r *http.Request, reason string) {
	conn, err := wsUpgrade(w, r)
	if err != nil {
		return
	}
	_ = conn.Close(context.Background(), wsClosePolicyViolation, reason)
}

// handleRealtime ports realtime_updates: resolve the caller from ?token=/bearer under the
// same AUTH_ENABLED decision every REST route applies (wsAuthenticateRealtime), accept, send
// the welcome frame, replay missed notifications, then answer ping/heartbeat/subscribe.
func handleRealtime(w http.ResponseWriter, r *http.Request) {
	token := r.URL.Query().Get("token")
	if token == "" {
		token = wsBearerToken(r)
	}
	result, reason := wsAuthenticateRealtime(r.Context(), token)
	if reason != "" {
		wsRejectUpgrade(w, r, reason)
		return
	}

	conn, err := wsUpgrade(w, r)
	if err != nil {
		return
	}
	defer conn.Close(context.Background(), 1000, "")

	ctx := context.Background()
	userID := *result.UserID
	email := ""
	if result.Email != nil {
		email = *result.Email
	}
	connectionID := wsRandInt(100000, 999999)
	clientID := "user_" + userID + "_" + value_objects.PyStr(connectionID)

	// Register the accepted socket so broadcasts can reach it (the registry was previously only
	// written by tests, so every fan-out was empty), and remove it on EVERY exit path - normal
	// close, read error or panic - because a stale entry would leak and a double delete is a no-op.
	user := &authdomain.User{ID: result.UserID, Username: userID, Email: email}
	routes.RegisterConnection(conn, user, clientID)
	defer routes.UnregisterConnection(conn)

	primary := entities.NewOrderedMap[any]()
	primary.Set("client_id", clientID)
	primary.Set("user_id", userID)
	primary.Set("user_email", email)
	primary.Set("scope", "branch")
	primary.Set("authenticated", true)
	_ = wsSend(ctx, conn, wsMessage("welcome-"+value_objects.PyStr(connectionID), "sync", 0, "connection", "welcome", primary, userID, clientID))

	wsReplayMissedNotifications(ctx, conn, userID)

	for {
		raw, err := conn.ReceiveText(ctx)
		if err != nil {
			return
		}
		decoded, err := entities.DecodeJSON([]byte(raw))
		if err != nil {
			primary := wsErrorData("Invalid JSON", "INVALID_JSON")
			_ = wsSend(ctx, conn, wsMessage(wsErrorID(), "error", wsRandInt(1000, 9999), "system", "error", primary, userID, clientID))
			continue
		}
		msg, _ := decoded.(*entities.OrderedMap[any])
		switch wsStr(wsGet(msg, "type")) {
		case "ping", "heartbeat":
			primary := entities.NewOrderedMap[any]()
			primary.Set("status", "alive")
			_ = wsSend(ctx, conn, wsMessage("pong-"+value_objects.PyStr(wsRandInt(100000, 999999)), "heartbeat", wsRandInt(1000, 9999), "system", "pong", primary, userID, clientID))
		case "subscribe":
			scope := wsStr(wsGet(msg, "scope"))
			if scope == "" {
				scope = "branch"
			}
			filters := wsGet(msg, "filters")
			if filters == nil {
				filters = entities.NewOrderedMap[any]()
			}
			primary := entities.NewOrderedMap[any]()
			primary.Set("scope", scope)
			primary.Set("filters", filters)
			_ = wsSend(ctx, conn, wsMessage("subscribed-"+value_objects.PyStr(wsRandInt(100000, 999999)), "sync", wsRandInt(1000, 9999), "subscription", "subscribed", primary, userID, clientID))
		default:
			primary := wsErrorData("Unknown message type: "+wsStr(wsGet(msg, "type")), "UNKNOWN_MESSAGE_TYPE")
			_ = wsSend(ctx, conn, wsMessage(wsErrorID(), "error", wsRandInt(1000, 9999), "system", "error", primary, userID, clientID))
		}
	}
}

// wsReplayMissedNotifications ports the offline replay block: send every stored
// notification, mark delivered on success, bump the attempt counter on failure.
func wsReplayMissedNotifications(ctx context.Context, conn *wsConn, userID string) {
	for _, notification := range routes.FetchMissedNotifications(ctx, userID, false, 100) {
		message, _ := notification.Get("message")
		if message == nil {
			continue
		}
		id, _ := notification.Get("id")
		idStr, _ := id.(string)
		if err := wsSend(ctx, conn, message); err != nil {
			if idStr != "" {
				routes.IncrementDeliveryAttempts(ctx, idStr)
			}
			continue
		}
		if idStr != "" {
			routes.MarkNotificationDelivered(ctx, idStr)
		}
	}
}

// handleConnector ports connector_ingest: authenticate from ?token= or the bearer
// header, require the sessions:write scope, accept, then serve hello/session/events.
// Both refusals COMPLETE the handshake and close with 1008 plus a reason (wsRejectUpgrade):
// a pre-upgrade 403 reaches a browser as close code 1006 with no reason. Authentication and
// authorization keep distinct reasons - see wsScopeMissingReason.
func handleConnector(sessions *database.SessionManager) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token := r.URL.Query().Get("token")
		if token == "" {
			token = wsBearerToken(r)
		}
		// The connector applies the SAME decision as every REST route and the realtime socket
		// (wsAuthenticateRealtime), rather than a ValidateTokenUniversal call of its own that
		// would demand a provider-minted token even with AUTH_ENABLED=false.
		result, reason := wsAuthenticateRealtime(r.Context(), token)
		if reason != "" {
			wsRejectUpgrade(w, r, reason)
			return
		}
		// Authorization is a separate, legitimate refusal. It is only decidable when auth is on:
		// with AUTH_ENABLED=false the shared decision resolves the development identity WITHOUT
		// reading the token, so no token-derived scope set exists to check and the socket must
		// not impose a scope rule the single decision never consulted.
		if auth.AuthEnabled() && !wsHasScope(result, routes.SessionStreamWriteScope) {
			wsRejectUpgrade(w, r, wsScopeMissingReason)
			return
		}

		conn, err := wsUpgrade(w, r)
		if err != nil {
			return
		}

		ctx := context.Background()
		userID := *result.UserID
		connectorID := ""
		known := map[string]string{}
		defer func() {
			_ = conn.Close(ctx, 1000, "")
			if connectorID == "" {
				return
			}
			if wsReleaseConnector(userID, connectorID) && sessions != nil {
				_ = session_stream.MarkOffline(ctx, sessions, userID, connectorID)
			}
		}()

		for {
			raw, err := conn.ReceiveText(ctx)
			if err != nil {
				return
			}
			if utf8.RuneCountInString(raw) > routes.SessionStreamMaxMsgChars {
				_ = wsSend(ctx, conn, wsConnectorError("message too large"))
				continue
			}
			decoded, err := entities.DecodeJSON([]byte(raw))
			if err != nil {
				_ = wsSend(ctx, conn, wsConnectorError("invalid json"))
				continue
			}
			msg, ok := decoded.(*entities.OrderedMap[any])
			if !ok {
				_ = wsSend(ctx, conn, wsConnectorError("invalid json"))
				continue
			}

			kind := wsStr(wsGet(msg, "type"))
			if kind == "hello" {
				cid := wsStrOrEmpty(wsGet(msg, "connector_id"))
				if !routes.ValidateConnectorID(cid) {
					_ = wsSend(ctx, conn, wsConnectorError("bad connector_id"))
					continue
				}
				if connectorID != "" && connectorID != cid {
					_ = wsSend(ctx, conn, wsConnectorError("connector_id already set"))
					continue
				}
				if connectorID == "" {
					connectorID = cid
					wsAcquireConnector(userID, cid)
				}
				ready := entities.NewOrderedMap[any]()
				ready.Set("type", "ready")
				ready.Set("connector_id", cid)
				_ = wsSend(ctx, conn, ready)
				continue
			}

			if connectorID == "" {
				_ = wsSend(ctx, conn, wsConnectorError("send hello first"))
				continue
			}

			switch kind {
			case "session":
				key := wsStrOrEmpty(wsGet(msg, "session_key"))
				if key == "" || len(key) > 255 {
					_ = wsSend(ctx, conn, wsConnectorError("bad session_key"))
					continue
				}
				name := wsStrOrEmpty(wsGet(msg, "name"))
				if name == "" {
					name = key
				}
				// The seat's identity as the connector observed it. Both-or-neither and the name rule
				// are enforced by the writer, so a frame naming half a pair is refused rather than
				// stored as a fact the rest of the system would have to guess about.
				row, err := session_stream.UpsertSession(ctx, sessions, userID, connectorID, key, name,
					wsOptString(wsGet(msg, "project")), wsOptString(wsGet(msg, "room")), wsOptString(wsGet(msg, "seat")))
				if err != nil {
					_ = wsSend(ctx, conn, wsConnectorError(wsAppendError(err)))
					continue
				}
				id, _ := row.Get("id")
				if idStr, ok := id.(string); ok {
					known[key] = idStr
				}
				lastSeq, _ := row.Get("last_seq")
				ack := entities.NewOrderedMap[any]()
				ack.Set("type", "session_ack")
				ack.Set("session_key", key)
				ack.Set("session_id", id)
				ack.Set("last_seq", lastSeq)
				_ = wsSend(ctx, conn, ack)
			case "events":
				sid, registered := known[wsStrOrEmpty(wsGet(msg, "session_key"))]
				events, isList := wsGet(msg, "events").([]any)
				if !registered || !isList {
					_ = wsSend(ctx, conn, wsConnectorError("unknown session"))
					continue
				}
				stored, err := session_stream.AppendEvents(ctx, sessions, userID, sid, events)
				if err != nil {
					_ = wsSend(ctx, conn, wsConnectorError(wsAppendError(err)))
					continue
				}
				published := make([]any, 0, len(stored))
				lastSeq := 0
				for _, ev := range stored {
					published = append(published, ev)
					if seq, ok := ev.Get("seq"); ok {
						lastSeq = wsInt(seq)
					}
				}
				session_stream.Hub.Publish(sid, published)
				ack := entities.NewOrderedMap[any]()
				ack.Set("type", "events_ack")
				ack.Set("session_id", sid)
				ack.Set("last_seq", lastSeq)
				_ = wsSend(ctx, conn, ack)
			default:
				_ = wsSend(ctx, conn, wsConnectorError("unknown type"))
			}
		}
	}
}

// wsAppendError maps a typed failure from the stream writers - append_events and the session
// frame - to the connector error text: the typed ValueError/PermissionError carry their message,
// anything else is internal. A refused seat identity therefore says which rule it broke rather
// than reporting "internal error".
func wsAppendError(err error) string {
	switch e := err.(type) {
	case *value_objects.ValueError:
		return e.Msg
	case *session_stream.PermissionError:
		return e.Msg
	default:
		return "internal error"
	}
}

// wsSend encodes v compactly and writes one text frame.
func wsSend(ctx context.Context, conn *wsConn, v any) error {
	data, err := value_objects.PyJSONDumpsCompact(v)
	if err != nil {
		return err
	}
	return conn.SendText(ctx, data)
}

// wsMessage builds the v2.0 envelope shared by the realtime replies.
func wsMessage(id, typ string, sequence int, entity, action string, primary any, userID, sessionID string) *entities.OrderedMap[any] {
	msg := entities.NewOrderedMap[any]()
	msg.Set("id", id)
	msg.Set("version", "2.0")
	msg.Set("type", typ)
	msg.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	msg.Set("sequence", sequence)
	payload := entities.NewOrderedMap[any]()
	payload.Set("entity", entity)
	payload.Set("action", action)
	data := entities.NewOrderedMap[any]()
	data.Set("primary", primary)
	payload.Set("data", data)
	msg.Set("payload", payload)
	meta := entities.NewOrderedMap[any]()
	meta.Set("source", "system")
	meta.Set("userId", userID)
	meta.Set("sessionId", sessionID)
	msg.Set("metadata", meta)
	return msg
}

func wsErrorData(message, code string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("message", message)
	m.Set("code", code)
	return m
}

func wsConnectorError(message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", "error")
	m.Set("error", message)
	return m
}

func wsErrorID() string {
	return "error-" + value_objects.PyStr(wsRandInt(100000, 999999))
}

// wsGet is msg.get(key) with nil for a missing key.
func wsGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// wsStr is str(value); a missing key becomes "None", matching Python's f-string.
func wsStr(v any) string { return value_objects.PyStr(v) }

// wsStrOrEmpty is the default "" form used where Python calls .get(key, "").
func wsStrOrEmpty(v any) string {
	if v == nil {
		return ""
	}
	return value_objects.PyStr(v)
}

// wsOptString is msg.get(key) or None for the repository's *string parameter.
func wsOptString(v any) *string {
	s := wsStrOrEmpty(v)
	if s == "" {
		return nil
	}
	return &s
}

func wsInt(v any) int {
	switch x := v.(type) {
	case int:
		return x
	case int64:
		return int(x)
	}
	return 0
}

func wsRandInt(min, max int) int { return min + rand.Intn(max-min+1) }

func wsBearerToken(r *http.Request) string {
	scheme, token, ok := strings.Cut(r.Header.Get("Authorization"), " ")
	if ok && strings.EqualFold(scheme, "bearer") {
		return strings.TrimSpace(token)
	}
	return ""
}

// wsHasScope checks the unified validator's scopes list.
func wsHasScope(result auth.UnifiedAuthResult, scope string) bool {
	for _, s := range result.Scopes {
		if v, ok := s.(string); ok && v == scope {
			return true
		}
	}
	return false
}

// Open connector sockets per (user_id, connector_id). A reconnect opens the new
// socket before the old one is noticed closed, so sessions only go offline when the
// last socket for that connector closes (Python _open_connectors).
var (
	wsOpenConnectorsMu sync.Mutex
	wsOpenConnectors   = map[string]int{}
)

func wsConnectorKey(userID, connectorID string) string { return userID + "\x00" + connectorID }

func wsAcquireConnector(userID, connectorID string) {
	wsOpenConnectorsMu.Lock()
	wsOpenConnectors[wsConnectorKey(userID, connectorID)]++
	wsOpenConnectorsMu.Unlock()
}

func wsReleaseConnector(userID, connectorID string) bool {
	key := wsConnectorKey(userID, connectorID)
	wsOpenConnectorsMu.Lock()
	defer wsOpenConnectorsMu.Unlock()
	left := wsOpenConnectors[key] - 1
	if left > 0 {
		wsOpenConnectors[key] = left
		return false
	}
	delete(wsOpenConnectors, key)
	return true
}

// wsConn is the RFC 6455 server side of one hijacked connection. It satisfies
// wslib.WebSocket so the routes helpers can send to it, and ClientHost/ClientPort so
// the routes authorization audit can report the peer.
type wsConn struct {
	conn net.Conn
	br   *bufio.Reader
	bw   *bufio.Writer
	mu   sync.Mutex

	clientHost string
	clientPort int
}

var _ wslib.WebSocket = (*wsConn)(nil)

func newWSConn(conn net.Conn, br *bufio.Reader) *wsConn {
	host, port := wsRemoteAddr(conn.RemoteAddr())
	return &wsConn{conn: conn, br: br, bw: bufio.NewWriter(conn), clientHost: host, clientPort: port}
}

// Accept is a no-op: wsUpgrade completes the HTTP upgrade before the connection is
// handed to a receive loop.
func (c *wsConn) Accept(context.Context) error { return nil }

func (c *wsConn) ClientHost() string { return c.clientHost }
func (c *wsConn) ClientPort() int    { return c.clientPort }

func (c *wsConn) Close(_ context.Context, code int, reason string) error {
	if code == 0 {
		code = 1000
	}
	payload := make([]byte, 0, 2+len(reason))
	payload = binary.BigEndian.AppendUint16(payload, uint16(code))
	payload = append(payload, reason...)
	_ = c.writeFrame(wsOpClose, payload)
	return c.conn.Close()
}

func (c *wsConn) SendText(_ context.Context, data string) error {
	return c.writeFrame(wsOpText, []byte(data))
}

// ReceiveText returns the next text (or binary) message. Control frames are handled
// inline; a close frame is answered and reported as *wslib.WebSocketDisconnect.
func (c *wsConn) ReceiveText(context.Context) (string, error) {
	text := []byte{}
	fragmented := false
	for {
		fin, opcode, payload, err := c.readFrame()
		if err != nil {
			return "", err
		}
		switch opcode {
		case wsOpPing:
			if err := c.writeFrame(wsOpPong, payload); err != nil {
				return "", err
			}
		case wsOpPong:
		case wsOpClose:
			code, reason := 1000, ""
			if len(payload) >= 2 {
				code = int(binary.BigEndian.Uint16(payload[:2]))
			}
			if len(payload) > 2 {
				reason = string(payload[2:])
			}
			_ = c.writeFrame(wsOpClose, payload)
			return "", &wslib.WebSocketDisconnect{Code: code, Reason: reason}
		case wsOpContinuation:
			if !fragmented {
				return "", &wslib.WebSocketDisconnect{Code: 1002, Reason: "unexpected continuation"}
			}
			if len(text)+len(payload) > wsMaxMessageBytes {
				return "", fmt.Errorf("websocket message too large")
			}
			text = append(text, payload...)
			if fin {
				return string(text), nil
			}
		case wsOpText, wsOpBinary:
			if fin {
				return string(payload), nil
			}
			fragmented = true
			text = append(text[:0], payload...)
		default:
			return "", &wslib.WebSocketDisconnect{Code: 1002, Reason: "unsupported opcode"}
		}
	}
}

func (c *wsConn) readFrame() (bool, byte, []byte, error) {
	header := make([]byte, 2)
	if _, err := io.ReadFull(c.br, header); err != nil {
		return false, 0, nil, err
	}
	fin := header[0]&0x80 != 0
	opcode := header[0] & 0x0f
	masked := header[1]&0x80 != 0
	length := int64(header[1] & 0x7f)
	switch length {
	case 126:
		ext := make([]byte, 2)
		if _, err := io.ReadFull(c.br, ext); err != nil {
			return false, 0, nil, err
		}
		length = int64(binary.BigEndian.Uint16(ext))
	case 127:
		ext := make([]byte, 8)
		if _, err := io.ReadFull(c.br, ext); err != nil {
			return false, 0, nil, err
		}
		length = int64(binary.BigEndian.Uint64(ext))
	}
	if length > wsMaxMessageBytes {
		return false, 0, nil, fmt.Errorf("websocket frame too large: %d", length)
	}
	var mask [4]byte
	if masked {
		if _, err := io.ReadFull(c.br, mask[:]); err != nil {
			return false, 0, nil, err
		}
	}
	payload := make([]byte, length)
	if _, err := io.ReadFull(c.br, payload); err != nil {
		return false, 0, nil, err
	}
	if masked {
		for i := range payload {
			payload[i] ^= mask[i%4]
		}
	}
	return fin, opcode, payload, nil
}

func (c *wsConn) writeFrame(opcode byte, payload []byte) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	header := make([]byte, 0, 10)
	header = append(header, 0x80|opcode)
	switch length := len(payload); {
	case length < 126:
		header = append(header, byte(length))
	case length < 65536:
		header = append(header, 126, byte(length>>8), byte(length))
	default:
		header = append(header, 127)
		header = binary.BigEndian.AppendUint64(header, uint64(length))
	}
	if _, err := c.bw.Write(header); err != nil {
		return err
	}
	if _, err := c.bw.Write(payload); err != nil {
		return err
	}
	return c.bw.Flush()
}

// wsUpgrade hijacks the HTTP connection and completes the RFC 6455 handshake.
func wsUpgrade(w http.ResponseWriter, r *http.Request) (*wsConn, error) {
	if !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") ||
		!wsHeaderToken(r.Header.Get("Connection"), "upgrade") ||
		r.Header.Get("Sec-WebSocket-Key") == "" {
		http.Error(w, "Expected WebSocket upgrade", http.StatusBadRequest)
		return nil, fmt.Errorf("not a websocket upgrade")
	}
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "WebSocket not supported", http.StatusInternalServerError)
		return nil, fmt.Errorf("response writer does not support hijacking")
	}
	netConn, bufrw, err := hijacker.Hijack()
	if err != nil {
		return nil, err
	}
	var extraHeaders strings.Builder
	if origin := w.Header().Get("Access-Control-Allow-Origin"); origin != "" {
		extraHeaders.WriteString("Access-Control-Allow-Origin: " + origin + "\r\n")
	}
	if creds := w.Header().Get("Access-Control-Allow-Credentials"); creds != "" {
		extraHeaders.WriteString("Access-Control-Allow-Credentials: " + creds + "\r\n")
	}
	_, err = fmt.Fprintf(bufrw,
		"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n%s\r\n",
		wsAcceptKey(r.Header.Get("Sec-WebSocket-Key")),
		extraHeaders.String())
	if err == nil {
		err = bufrw.Flush()
	}
	if err != nil {
		_ = netConn.Close()
		return nil, err
	}
	return newWSConn(netConn, bufrw.Reader), nil
}

// wsHeaderToken reports whether a comma-separated header contains token.
func wsHeaderToken(header, token string) bool {
	for _, part := range strings.Split(header, ",") {
		if strings.EqualFold(strings.TrimSpace(part), token) {
			return true
		}
	}
	return false
}

func wsAcceptKey(key string) string {
	sum := sha1.Sum([]byte(key + wsGUID))
	return base64.StdEncoding.EncodeToString(sum[:])
}

func wsRemoteAddr(addr net.Addr) (string, int) {
	if addr == nil {
		return "unknown", 0
	}
	host, portStr, err := net.SplitHostPort(addr.String())
	if err != nil {
		return addr.String(), 0
	}
	port, _ := strconv.Atoi(portStr)
	return host, port
}
