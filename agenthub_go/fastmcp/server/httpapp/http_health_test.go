package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/config"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// healthTestWS satisfies the registry's socket contract; these tests never send on it.
// The id field keeps each instance non-zero-sized so two fakes get distinct addresses
// and therefore distinct registry map keys (zero-size struct pointers can alias).
type healthTestWS struct{ id string }

func (*healthTestWS) Accept(context.Context) error             { return nil }
func (*healthTestWS) Close(context.Context, int, string) error { return nil }
func (*healthTestWS) SendText(context.Context, string) error   { return nil }
func (*healthTestWS) ReceiveText(context.Context) (string, error) {
	return "", nil
}

func healthStrPtr(s string) *string { return &s }

// registerHealthTestConnection registers a socket through the same exported entry
// point the WebSocket handler uses, so /health is read against the real registry.
func registerHealthTestConnection(id string) (*healthTestWS, func()) {
	ws := &healthTestWS{id: id}
	routes.RegisterConnection(ws, &authdomain.User{ID: healthStrPtr(id)}, "client-"+id)
	return ws, func() { routes.UnregisterConnection(ws) }
}

// doHealthRequest calls handleHealth and decodes the JSON body.
func doHealthRequest(t *testing.T) map[string]any {
	t.Helper()
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	handleHealth(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want 200", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("GET /health Content-Type = %q, want application/json", ct)
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("GET /health body %q is not JSON: %v", rec.Body.String(), err)
	}
	return body
}

func assertHealthKeys(t *testing.T, got map[string]any, want ...string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for _, k := range want {
		if _, ok := got[k]; !ok {
			t.Fatalf("missing key %q in %v", k, got)
		}
	}
}

func healthConnectionCount(t *testing.T, body map[string]any) float64 {
	t.Helper()
	connections, ok := body["connections"].(map[string]any)
	if !ok {
		t.Fatalf("connections = %v (%T), want object", body["connections"], body["connections"])
	}
	got, ok := connections["active_connections"].(float64)
	if !ok {
		t.Fatalf("connections.active_connections = %v (%T), want number", connections["active_connections"], connections["active_connections"])
	}
	return got
}

// TestHealthReportsTheLiveRegistry is the anti-regression test: it registers real
// sockets through routes.RegisterConnection and asserts the handler's figures move
// with the registry. A /health that reads a stale seam, a constant, or a detached
// provider fails here.
func TestHealthReportsTheLiveRegistry(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	baseline := routes.ConnectionCount()

	_, unregisterOne := registerHealthTestConnection("u-health-1")
	defer unregisterOne()

	body := doHealthRequest(t)
	assertHealthKeys(t, body, "status", "timestamp", "server", "version", "auth_enabled", "connections", "status_broadcasting")
	if got := body["status"]; got != "healthy" {
		t.Fatalf("status = %v, want %q", got, "healthy")
	}
	if got := body["version"]; got != healthVersion {
		t.Fatalf("version = %v, want %q", got, healthVersion)
	}

	connections, ok := body["connections"].(map[string]any)
	if !ok {
		t.Fatalf("connections = %v (%T), want object", body["connections"], body["connections"])
	}
	assertHealthKeys(t, connections, "active_connections", "uptime_seconds")
	for _, dropped := range []string{"server_restart_count", "recommended_action"} {
		if _, ok := connections[dropped]; ok {
			t.Fatalf("connections.%s must not be reported: the Go server has no source for it", dropped)
		}
	}
	if got := healthConnectionCount(t, body); got != float64(baseline+1) {
		t.Fatalf("connections.active_connections = %v, want %v (registry count after one registration)", got, baseline+1)
	}
	if got, ok := connections["uptime_seconds"].(float64); !ok || got < 0 {
		t.Fatalf("connections.uptime_seconds = %v (%T), want a non-negative number", connections["uptime_seconds"], connections["uptime_seconds"])
	}

	broadcasting, ok := body["status_broadcasting"].(map[string]any)
	if !ok {
		t.Fatalf("status_broadcasting = %v (%T), want object", body["status_broadcasting"], body["status_broadcasting"])
	}
	assertHealthKeys(t, broadcasting, "active", "registered_clients")
	for _, dropped := range []string{"last_broadcast", "last_broadcast_time", "error"} {
		if _, ok := broadcasting[dropped]; ok {
			t.Fatalf("status_broadcasting.%s must not be reported: the Go server has no source for it", dropped)
		}
	}
	if got, ok := broadcasting["active"].(bool); !ok || !got {
		t.Fatalf("status_broadcasting.active = %v (%T), want true", broadcasting["active"], broadcasting["active"])
	}
	if got, ok := broadcasting["registered_clients"].(float64); !ok || got != float64(baseline+1) {
		t.Fatalf("status_broadcasting.registered_clients = %v, want %v", broadcasting["registered_clients"], baseline+1)
	}

	// A second registration must move both figures: a hard-coded value is caught here.
	_, unregisterTwo := registerHealthTestConnection("u-health-2")
	defer unregisterTwo()
	if got := healthConnectionCount(t, doHealthRequest(t)); got != float64(baseline+2) {
		t.Fatalf("active_connections = %v with two registered sockets, want %v", got, baseline+2)
	}

	// Closing sockets must move the figures back down.
	unregisterTwo()
	unregisterOne()
	if got := healthConnectionCount(t, doHealthRequest(t)); got != float64(baseline) {
		t.Fatalf("active_connections = %v after every socket closed, want %v", got, baseline)
	}
}

func TestHealthAuthEnabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "yes")
	if got := doHealthRequest(t)["auth_enabled"]; got != true {
		t.Fatalf("AUTH_ENABLED=yes -> auth_enabled = %v, want true", got)
	}

	t.Setenv("AUTH_ENABLED", "off")
	if got := doHealthRequest(t)["auth_enabled"]; got != false {
		t.Fatalf("AUTH_ENABLED=off -> auth_enabled = %v, want false", got)
	}
}

// TestEveryVersionSurfaceReportsTheOneRelease is the anti-drift test for the release identity.
//
// Four surfaces here used to answer "which release is this?" three different ways: /health
// carried the deploy marker while the MCP surfaces carried the ported module's 0.0.2c or the
// Python framework's 2.1.0. A version string that disagrees with itself is how a deploy gets
// called complete when it is not, so every surface below must report config.ReleaseVersion.
func TestEveryVersionSurfaceReportsTheOneRelease(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")

	// 1. GET /health.
	healthVersionReported := doHealthRequest(t)["version"]
	if healthVersionReported != config.ReleaseVersion {
		t.Errorf("/health version = %v, want %q", healthVersionReported, config.ReleaseVersion)
	}

	// 2. MCP initialize -> result.serverInfo.version, the version a client sees first.
	app := newMCPTestApp(t)
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"initialize"}`, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("initialize status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			ServerInfo struct {
				Version string `json:"version"`
			} `json:"serverInfo"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode initialize: %v (%s)", err, rec.Body.String())
	}
	if wire.Result.ServerInfo.Version != config.ReleaseVersion {
		t.Errorf("initialize serverInfo.version = %q, want %q", wire.Result.ServerInfo.Version, config.ReleaseVersion)
	}

	// 3. POST /register -> server.version.
	registered := mcpRegisterResponse("sess-version", "http://example.com")
	serverInfo, _ := registered.Get("server")
	registerVersion, _ := serverInfo.(*entities.OrderedMap[any]).Get("version")
	if registerVersion != config.ReleaseVersion {
		t.Errorf("register server.version = %v, want %q", registerVersion, config.ReleaseVersion)
	}

	// 4. The connection-management health route, which the manage_connection tool returns.
	connectionHealth := routes.HealthCheck(nil)
	connectionVersion, _ := connectionHealth.Get("version")
	if connectionVersion != config.ReleaseVersion {
		t.Errorf("connection health version = %v, want %q", connectionVersion, config.ReleaseVersion)
	}

	// The fossils must be gone from every surface, not merely agree with each other.
	for _, got := range []any{healthVersionReported, wire.Result.ServerInfo.Version, registerVersion, connectionVersion} {
		if got == "0.0.2c" || got == "2.1.0" {
			t.Errorf("a version surface still reports the fossil %v", got)
		}
	}
}
