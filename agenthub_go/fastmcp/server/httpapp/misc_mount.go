// misc_mount.go mounts the remaining endpoints that live outside the route
// modules ported under fastmcp/server/routes:
//
//   - POST /register, POST /unregister, GET /registrations: the MCP client
//     registration surface http_server.py adds directly to the v2 FastAPI app.
//   - GET /ws/metrics: the Prometheus text endpoint of
//     server/routes/websocket_routes.py (router prefix "/ws").
//
// The three registration handlers in Python close over a per-app
// active_registrations dict; mountMiscRoutes keeps that state in a store created
// per call, so each mux owns its own registrations.
package httpapp

import (
	"encoding/json"
	"fmt"
	"math"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/server/metrics"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// mcpRegistrationTTLSeconds mirrors the 3600 second cleanup window of
// list_mcp_registrations.
const mcpRegistrationTTLSeconds = 3600

// miscPrometheusContentType is prometheus_client.CONTENT_TYPE_LATEST, the media type
// of websocket_routes.metrics().
const miscPrometheusContentType = "text/plain; version=0.0.4; charset=utf-8"

// mcpRegistration is the Python registration record.
type mcpRegistration struct {
	sessionID    string
	clientIP     string
	clientPort   int
	userAgent    string
	registeredAt float64
	lastActivity float64
}

// mcpRegistrationStore is the active_registrations dict of http_server.py,
// preserving insertion order and protecting concurrent access.
type mcpRegistrationStore struct {
	mu    sync.Mutex
	order []string
	byID  map[string]*mcpRegistration
}

// mountMiscRoutes registers the MCP registration endpoints and the WebSocket
// Prometheus metrics endpoint. Handler must call it once; the patterns are not
// registered anywhere else.
func mountMiscRoutes(mux *http.ServeMux) {
	store := &mcpRegistrationStore{byID: map[string]*mcpRegistration{}}

	mux.HandleFunc("POST /register", func(w http.ResponseWriter, r *http.Request) {
		sessionID := store.register(r)
		writeJSON(w, http.StatusOK, mcpRegisterResponse(sessionID, miscRequestBaseURL(r)))
	})
	mux.HandleFunc("POST /unregister", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, store.unregisterResponse(r))
	})
	mux.HandleFunc("GET /registrations", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, store.listResponse())
	})
	mux.HandleFunc("GET /ws/metrics", handleWebSocketMetrics)
}

// register ports register_mcp_client: mint a session id, record the client and
// return the session id.
func (s *mcpRegistrationStore) register(r *http.Request) string {
	now := miscPyTime()
	host, port := miscRequestClientAddr(r)
	sessionID := value_objects.NewUUIDv4()
	s.mu.Lock()
	s.byID[sessionID] = &mcpRegistration{
		sessionID:    sessionID,
		clientIP:     host,
		clientPort:   port,
		userAgent:    r.Header.Get("User-Agent"),
		registeredAt: now,
		lastActivity: now,
	}
	s.order = append(s.order, sessionID)
	s.mu.Unlock()
	return sessionID
}

// unregisterResponse ports unregister_mcp_client. An unreadable or non-object
// body is the Python except branch; a missing/unknown session id is the "Invalid
// session" branch.
func (s *mcpRegistrationStore) unregisterResponse(r *http.Request) *entities.OrderedMap[any] {
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body == nil {
		return miscErrorResponse("Unregistration failed", jsonDecodeErrorText(err))
	}
	sessionID, _ := body["session_id"].(string)
	if !s.unregister(sessionID) {
		return miscErrorResponse("Invalid session", "Session ID not found")
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", "Client unregistered successfully")
	return out
}

// jsonDecodeErrorText is str(e) of the decode exception; a JSON null body has no
// exception in Go but is an AttributeError in Python, so it keeps the None text.
func jsonDecodeErrorText(err error) string {
	if err != nil {
		return err.Error()
	}
	return "'NoneType' object has no attribute 'get'"
}

// unregister removes sessionID, reporting whether it was registered.
func (s *mcpRegistrationStore) unregister(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.byID[sessionID]; !ok {
		return false
	}
	delete(s.byID, sessionID)
	for i, sid := range s.order {
		if sid == sessionID {
			s.order = append(s.order[:i], s.order[i+1:]...)
			break
		}
	}
	return true
}

// listResponse ports list_mcp_registrations: drop every session idle for more
// than an hour, then report the remaining ones in insertion order.
func (s *mcpRegistrationStore) listResponse() *entities.OrderedMap[any] {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := miscPyTime()
	kept := s.order[:0]
	for _, sid := range s.order {
		reg := s.byID[sid]
		if now-reg.lastActivity > mcpRegistrationTTLSeconds {
			delete(s.byID, sid)
			continue
		}
		kept = append(kept, sid)
	}
	s.order = kept

	sessions := make([]any, 0, len(s.order))
	details := make([]any, 0, len(s.order))
	for _, sid := range s.order {
		reg := s.byID[sid]
		sessions = append(sessions, sid)
		detail := entities.NewOrderedMap[any]()
		detail.Set("session_id", reg.sessionID)
		detail.Set("client_ip", reg.clientIP)
		detail.Set("user_agent", reg.userAgent)
		detail.Set("registered_at", reg.registeredAt)
		detail.Set("last_activity", reg.lastActivity)
		details = append(details, detail)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("active_registrations", len(s.order))
	out.Set("sessions", sessions)
	out.Set("details", details)
	return out
}

// mcpRegisterResponse is the register_mcp_client return dict.
func mcpRegisterResponse(sessionID, baseURL string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("session_id", sessionID)

	server := entities.NewOrderedMap[any]()
	server.Set("name", "agenthub-server")
	server.Set("version", config.ReleaseVersion)
	server.Set("protocol_version", mcpProtocolVersion)
	out.Set("server", server)

	endpoints := entities.NewOrderedMap[any]()
	endpoints.Set("mcp", baseURL+"/mcp/")
	endpoints.Set("initialize", baseURL+"/mcp/initialize")
	endpoints.Set("tools", baseURL+"/mcp/tools/list")
	endpoints.Set("health", baseURL+"/health")
	out.Set("endpoints", endpoints)

	out.Set("transport", "streamable-http")

	authentication := entities.NewOrderedMap[any]()
	authentication.Set("required", true)
	authentication.Set("type", "Bearer")
	authentication.Set("header", "Authorization")
	authentication.Set("format", "Bearer YOUR_JWT_TOKEN_HERE")
	out.Set("authentication", authentication)

	capabilities := entities.NewOrderedMap[any]()
	capabilities.Set("tools", true)
	capabilities.Set("resources", true)
	capabilities.Set("prompts", true)
	capabilities.Set("logging", true)
	capabilities.Set("progress", true)
	out.Set("capabilities", capabilities)

	instructions := entities.NewOrderedMap[any]()
	instructions.Set("next_step", "Initialize connection at /mcp/initialize endpoint")
	instructions.Set("authentication", "Include JWT token in Authorization header")
	instructions.Set("protocol", "Use MCP protocol for all subsequent requests")
	out.Set("instructions", instructions)
	return out
}

// miscErrorResponse is the {"error", "message"} dict both handlers return on the
// invalid/except branches.
func miscErrorResponse(message, detail string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("error", message)
	out.Set("message", detail)
	return out
}

// handleWebSocketMetrics ports websocket_routes.metrics(). The Go port keeps its
// Prometheus registry in-process (fastmcp/server/metrics) and exposes the
// connection gauge and retry counter from GetMetricsSummary.
func handleWebSocketMetrics(w http.ResponseWriter, _ *http.Request) {
	summary := metrics.GetMetricsSummary()
	active := miscSummaryFloat(summary, "active_connections")
	authenticated := miscSummaryFloat(summary, "authenticated_connections")
	retries := miscSummaryFloat(summary, "total_retries")

	var b strings.Builder
	b.WriteString("# HELP websocket_connections Number of active WebSocket connections\n")
	b.WriteString("# TYPE websocket_connections gauge\n")
	fmt.Fprintf(&b, "websocket_connections{status=\"active\"} %s\n", miscPromFloat(active))
	fmt.Fprintf(&b, "websocket_connections{status=\"authenticated\"} %s\n", miscPromFloat(authenticated))
	b.WriteString("# HELP websocket_message_retries_total Total number of message retry attempts\n")
	b.WriteString("# TYPE websocket_message_retries_total counter\n")
	fmt.Fprintf(&b, "websocket_message_retries_total %s\n", miscPromFloat(retries))

	w.Header().Set("Content-Type", miscPrometheusContentType)
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(b.String()))
}

// miscPromFloat renders a metric value the way prometheus_client does: whole numbers
// keep one decimal (3.0), everything else uses the shortest representation.
func miscPromFloat(v float64) string {
	if v == math.Trunc(v) && math.Abs(v) < 1e21 {
		return strconv.FormatFloat(v, 'f', 1, 64)
	}
	return strconv.FormatFloat(v, 'g', -1, 64)
}

// miscSummaryFloat reads a float64 metric from GetMetricsSummary.
func miscSummaryFloat(m *entities.OrderedMap[any], key string) float64 {
	if m == nil {
		return 0
	}
	v, _ := m.Get(key)
	f, _ := v.(float64)
	return f
}

// miscRequestBaseURL is request.url.scheme://request.url.netloc.
func miscRequestBaseURL(r *http.Request) string {
	scheme := "http"
	if r.TLS != nil {
		scheme = "https"
	}
	return scheme + "://" + r.Host
}

// miscRequestClientAddr is request.client.host/port, or "unknown"/0 when the peer is
// unknown (Python's `if request.client else`).
func miscRequestClientAddr(r *http.Request) (string, int) {
	if r.RemoteAddr == "" {
		return "unknown", 0
	}
	host, portStr, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr, 0
	}
	port, _ := strconv.Atoi(portStr)
	return host, port
}

// miscPyTime is time.time() with sub-second precision.
func miscPyTime() float64 {
	return float64(time.Now().UnixNano()) / 1e9
}
