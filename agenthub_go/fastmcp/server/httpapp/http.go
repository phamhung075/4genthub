// Package httpapp composes the Go HTTP server: it adapts the logic functions in
// server/routes to net/http, resolves the authenticated user and wires repositories,
// services and hooks (the composition root Python spreads across http_server.py and the
// FastAPI dependency graph).
package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// writeJSON writes body the way Starlette's JSONResponse does (compact separators).
func writeJSON(w http.ResponseWriter, status int, body *entities.OrderedMap[any]) {
	out, err := value_objects.PyJSONDumpsCompact(body)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write([]byte(out))
}

// writeDetail writes FastAPI's {"detail": ...} error body.
func writeDetail(w http.ResponseWriter, status int, detail string) {
	b, _ := json.Marshal(map[string]string{"detail": detail})
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(b)
}

// writeResult writes a routes-layer result: success 200, *auth.HTTPException as its status.
func writeResult(w http.ResponseWriter, body *entities.OrderedMap[any], err error) {
	if err != nil {
		if he, ok := err.(*auth.HTTPException); ok {
			writeDetail(w, he.StatusCode, he.Detail)
			return
		}
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	writeJSON(w, http.StatusOK, body)
}

// writeSliceResult writes a list result or HTTPException status.
func writeSliceResult(w http.ResponseWriter, list []*entities.OrderedMap[any], err error) {
	writeSliceBody(w, "", list, err)
}

// writeKeyedSliceResult answers {key: [...]}, the shape of the Python routes that return
// {"sessions": rows} or {"events": rows}.
func writeKeyedSliceResult(w http.ResponseWriter, key string, list []*entities.OrderedMap[any], err error) {
	writeSliceBody(w, key, list, err)
}

// writeSliceBody writes list as a JSON array, wrapped as {key: array} when key is not empty.
func writeSliceBody(w http.ResponseWriter, key string, list []*entities.OrderedMap[any], err error) {
	if err != nil {
		if he, ok := err.(*auth.HTTPException); ok {
			writeDetail(w, he.StatusCode, he.Detail)
			return
		}
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	var out []string
	for _, m := range list {
		s, _ := value_objects.PyJSONDumpsCompact(m)
		out = append(out, s)
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	body := "[" + strings.Join(out, ",") + "]"
	if key != "" {
		body = "{" + strconv.Quote(key) + ":" + body + "}"
	}
	_, _ = w.Write([]byte(body))
}

// currentUser is Depends(get_current_user): HTTPBearer rejects a missing bearer header
// with 403 "Not authenticated" before the provider logic runs.
func currentUser(w http.ResponseWriter, r *http.Request) (*authdomain.User, bool) {
	h := r.Header.Get("Authorization")
	scheme, token, _ := strings.Cut(h, " ")
	if !strings.EqualFold(scheme, "bearer") || strings.TrimSpace(token) == "" {
		writeDetail(w, http.StatusForbidden, "Not authenticated")
		return nil, false
	}
	token = strings.TrimSpace(token)
	user, err := authinterface.GetCurrentUser(r.Context(), &token, nil)
	if err != nil {
		if he, ok := err.(*auth.HTTPException); ok {
			writeDetail(w, he.StatusCode, he.Detail)
		} else {
			writeDetail(w, http.StatusUnauthorized, err.Error())
		}
		return nil, false
	}
	return user, true
}

// writeMissing is FastAPI's 422 for missing required parameters; where is "body" (form
// fields) or "query".
func writeMissing(w http.ResponseWriter, where string, fields ...string) {
	items := make([]map[string]any, 0, len(fields))
	for _, f := range fields {
		items = append(items, map[string]any{"type": "missing", "loc": []string{where, f}, "msg": "Field required", "input": nil})
	}
	b, _ := json.Marshal(map[string]any{"detail": items})
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnprocessableEntity)
	_, _ = w.Write(b)
}

// missingForm lists the required form fields absent from r.PostForm.
func missingForm(r *http.Request, fields ...string) []string {
	var out []string
	for _, f := range fields {
		if !r.PostForm.Has(f) {
			out = append(out, f)
		}
	}
	return out
}

// authenticateUser extracts user from Authorization header if present.
func authenticateUser(ctx context.Context, r *http.Request) (*authdomain.User, error) {
	h := r.Header.Get("Authorization")
	scheme, token, _ := strings.Cut(h, " ")
	if !strings.EqualFold(scheme, "bearer") || strings.TrimSpace(token) == "" {
		return nil, nil
	}
	token = strings.TrimSpace(token)
	return authinterface.GetCurrentUser(ctx, &token, nil)
}

// healthServerName is the FastMCP server name (mcp_entry_point.py server = FastMCP(name=...)).
const healthServerName = "agenthub - Task Management & Agent Orchestration"

// healthVersion is the release the server reports on /health. Bump it with every
// change that must be confirmable after a deploy: the Docker build context has
// no .git, so no commit id can be embedded.
const healthVersion = "0.0.16"

// HealthStatusProvider supplies the connection figures the Python /health
// handler reads from get_connection_manager() and get_status_broadcaster(). The
// server package registers an implementation; httpapp cannot import server
// because server imports httpapp (mcp_entry_point.go).
type HealthStatusProvider interface {
	GetConnectionStats() *entities.OrderedMap[any]
	GetReconnectionInfo() *entities.OrderedMap[any]
	GetLastStatus() *entities.OrderedMap[any]
	GetClientCount() int
}

var globalHealthStatusProvider HealthStatusProvider

// SetHealthStatusProvider registers the provider used by GET /health.
func SetHealthStatusProvider(p HealthStatusProvider) {
	globalHealthStatusProvider = p
}

// handleHealth is GET /health, the custom route health_endpoint of
// mcp_entry_point.py. JSONResponse defaults to 200.
func handleHealth(w http.ResponseWriter, _ *http.Request) {
	body := entities.NewOrderedMap[any]()
	body.Set("status", "healthy")
	body.Set("timestamp", float64(time.Now().UnixNano())/1e9)
	body.Set("server", healthServerName)
	body.Set("version", healthVersion)
	body.Set("auth_enabled", healthAuthEnabled())

	provider := globalHealthStatusProvider
	if provider == nil {
		// Python's except branch when get_connection_manager() raises.
		body.Set("connections", healthErrorMap("connection manager unavailable"))
		body.Set("status_broadcasting", healthBroadcastingErrorMap("connection manager unavailable"))
	} else {
		body.Set("connections", healthConnections(provider))
		body.Set("status_broadcasting", healthStatusBroadcasting(provider))
	}
	writeJSON(w, http.StatusOK, body)
}

// healthAuthEnabled mirrors os.environ.get("AUTH_ENABLED", "true").lower() in
// ("true", "1", "yes", "on").
func healthAuthEnabled() bool {
	authStatus, ok := os.LookupEnv("AUTH_ENABLED")
	if !ok {
		authStatus = "true"
	}
	switch strings.ToLower(authStatus) {
	case "true", "1", "yes", "on":
		return true
	}
	return false
}

// healthConnections builds health_data["connections"].
func healthConnections(p HealthStatusProvider) *entities.OrderedMap[any] {
	stats := p.GetConnectionStats()
	reconnection := p.GetReconnectionInfo()
	connections := healthField(stats, "connections")
	serverInfo := healthField(stats, "server_info")
	out := entities.NewOrderedMap[any]()
	out.Set("active_connections", healthGet(connections, "active_connections"))
	out.Set("server_restart_count", healthGet(serverInfo, "restart_count"))
	out.Set("uptime_seconds", healthGet(serverInfo, "uptime_seconds"))
	out.Set("recommended_action", healthGet(reconnection, "recommended_action"))
	return out
}

// healthStatusBroadcasting builds health_data["status_broadcasting"].
func healthStatusBroadcasting(p HealthStatusProvider) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("active", true)
	out.Set("registered_clients", p.GetClientCount())
	lastStatus := p.GetLastStatus()
	if lastStatus == nil {
		out.Set("last_broadcast", any(nil))
		out.Set("last_broadcast_time", any(nil))
		return out
	}
	out.Set("last_broadcast", healthGet(lastStatus, "event_type"))
	out.Set("last_broadcast_time", healthGet(lastStatus, "timestamp"))
	return out
}

// healthErrorMap is Python's {"error": str(e)} connection fallback.
func healthErrorMap(msg string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("error", msg)
	return out
}

// healthBroadcastingErrorMap is Python's {"active": False, "error": str(e)} fallback.
func healthBroadcastingErrorMap(msg string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("active", false)
	out.Set("error", msg)
	return out
}

// healthField returns the nested map at key, or nil when it is absent.
func healthField(m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok {
		return nil
	}
	nested, _ := v.(*entities.OrderedMap[any])
	return nested
}

// healthGet reads key from an optional map (None when the map or key is absent).
func healthGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}
