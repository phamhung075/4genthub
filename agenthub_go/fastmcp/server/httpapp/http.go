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
	"agenthub/fastmcp/config"
	"agenthub/fastmcp/server/routes"
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
// The description after the dash is the one-line product description the frontend
// landed with directive G (agenthub-frontend/src/components/Header.tsx:125); keep the
// two in step rather than phrasing a third one here.
const healthServerName = config.ServerName

// healthVersion is the release the server reports on /health, and it is the same value every
// other version surface reports: config.ReleaseVersion, defined once. Bump THAT with every
// change that must be confirmable after a deploy (the Docker build context has no .git, so no
// commit id can be embedded), and make it the last commit in the set before a deploy.
const healthVersion = config.ReleaseVersion

// healthProcessStart is the process start time captured at init; /health reports seconds since it.
// The Python handler read uptime from the connection manager, an object the Go server never had.
var healthProcessStart = time.Now()

// handleHealth is GET /health, the custom route health_endpoint of
// mcp_entry_point.py. JSONResponse defaults to 200.
func handleHealth(w http.ResponseWriter, _ *http.Request) {
	body := entities.NewOrderedMap[any]()
	body.Set("status", "healthy")
	body.Set("timestamp", float64(time.Now().UnixNano())/1e9)
	body.Set("server", healthServerName)
	body.Set("version", healthVersion)
	body.Set("auth_enabled", healthAuthEnabled())

	// Read the live registry the realtime fan-out itself uses
	// (server/routes/websocket_routes.go). There is no provider seam to leave
	// unassigned: a seam that production never assigns reported a false
	// "connection manager unavailable" while fan-out worked fine.
	count := routes.ConnectionCount()
	body.Set("connections", healthConnections(count))
	body.Set("status_broadcasting", healthStatusBroadcasting(count))
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

// healthConnections builds health_data["connections"] from the live registry.
// Only figures the Go server actually measures are reported; the Python-era
// server_restart_count and recommended_action had no Go source.
func healthConnections(count int) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("active_connections", count)
	out.Set("uptime_seconds", time.Since(healthProcessStart).Seconds())
	return out
}

// healthStatusBroadcasting builds health_data["status_broadcasting"]. active is
// ASSERTED, not measured: the fan-out registry is package-level and lives exactly
// as long as the process, so active is true by construction while the server
// serves - deliberately NOT the old defect's shape, which asserted a false
// UNAVAILABLE state while fan-out worked. If the fan-out ever becomes stoppable
// while the server stays up, this field needs a real source instead of the
// constant. registered_clients is the same registry count /health reports as
// active_connections.
func healthStatusBroadcasting(count int) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("active", true)
	out.Set("registered_clients", count)
	return out
}
