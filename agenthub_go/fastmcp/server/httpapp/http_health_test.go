package httpapp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// fakeHealthStatusProvider is the connection source /health uses in tests.
type fakeHealthStatusProvider struct {
	lastStatus *entities.OrderedMap[any]
	clients    int
}

func (f fakeHealthStatusProvider) GetConnectionStats() *entities.OrderedMap[any] {
	connections := entities.NewOrderedMap[any]()
	connections.Set("active_connections", 2)
	serverInfo := entities.NewOrderedMap[any]()
	serverInfo.Set("restart_count", 1)
	serverInfo.Set("uptime_seconds", 12.5)
	stats := entities.NewOrderedMap[any]()
	stats.Set("connections", connections)
	stats.Set("server_info", serverInfo)
	return stats
}

func (f fakeHealthStatusProvider) GetReconnectionInfo() *entities.OrderedMap[any] {
	info := entities.NewOrderedMap[any]()
	info.Set("recommended_action", "continue")
	return info
}

func (f fakeHealthStatusProvider) GetLastStatus() *entities.OrderedMap[any] {
	return f.lastStatus
}

func (f fakeHealthStatusProvider) GetClientCount() int {
	return f.clients
}

// swapHealthStatusProvider registers p and returns a restore func.
func swapHealthStatusProvider(p HealthStatusProvider) func() {
	previous := globalHealthStatusProvider
	SetHealthStatusProvider(p)
	return func() { SetHealthStatusProvider(previous) }
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

func TestHealthPayloadSuccessShape(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	lastStatus := entities.NewOrderedMap[any]()
	lastStatus.Set("event_type", "connection_health")
	lastStatus.Set("timestamp", 1700000000.25)
	restore := swapHealthStatusProvider(fakeHealthStatusProvider{lastStatus: lastStatus, clients: 3})
	defer restore()

	body := doHealthRequest(t)

	assertHealthKeys(t, body, "status", "timestamp", "server", "version", "auth_enabled", "connections", "status_broadcasting")

	if got := body["status"]; got != "healthy" {
		t.Fatalf("status = %v, want %q", got, "healthy")
	}
	if _, ok := body["timestamp"].(float64); !ok {
		t.Fatalf("timestamp = %v (%T), want number", body["timestamp"], body["timestamp"])
	}
	if got := body["server"]; got != healthServerName {
		t.Fatalf("server = %v, want %q", got, healthServerName)
	}
	if got := body["version"]; got != "0.0.6" {
		t.Fatalf("version = %v, want %q", got, "0.0.6")
	}
	if got, ok := body["auth_enabled"].(bool); !ok || !got {
		t.Fatalf("auth_enabled = %v (%T), want true", body["auth_enabled"], body["auth_enabled"])
	}

	connections, ok := body["connections"].(map[string]any)
	if !ok {
		t.Fatalf("connections = %v (%T), want object", body["connections"], body["connections"])
	}
	assertHealthKeys(t, connections, "active_connections", "server_restart_count", "uptime_seconds", "recommended_action")
	if got, ok := connections["active_connections"].(float64); !ok || got != 2 {
		t.Fatalf("connections.active_connections = %v (%T), want 2", connections["active_connections"], connections["active_connections"])
	}
	if got, ok := connections["server_restart_count"].(float64); !ok || got != 1 {
		t.Fatalf("connections.server_restart_count = %v (%T), want 1", connections["server_restart_count"], connections["server_restart_count"])
	}
	if got, ok := connections["uptime_seconds"].(float64); !ok || got != 12.5 {
		t.Fatalf("connections.uptime_seconds = %v (%T), want 12.5", connections["uptime_seconds"], connections["uptime_seconds"])
	}
	if got := connections["recommended_action"]; got != "continue" {
		t.Fatalf("connections.recommended_action = %v, want %q", got, "continue")
	}

	broadcasting, ok := body["status_broadcasting"].(map[string]any)
	if !ok {
		t.Fatalf("status_broadcasting = %v (%T), want object", body["status_broadcasting"], body["status_broadcasting"])
	}
	assertHealthKeys(t, broadcasting, "active", "registered_clients", "last_broadcast", "last_broadcast_time")
	if got, ok := broadcasting["active"].(bool); !ok || !got {
		t.Fatalf("status_broadcasting.active = %v (%T), want true", broadcasting["active"], broadcasting["active"])
	}
	if got, ok := broadcasting["registered_clients"].(float64); !ok || got != 3 {
		t.Fatalf("status_broadcasting.registered_clients = %v (%T), want 3", broadcasting["registered_clients"], broadcasting["registered_clients"])
	}
	if got := broadcasting["last_broadcast"]; got != "connection_health" {
		t.Fatalf("status_broadcasting.last_broadcast = %v, want %q", got, "connection_health")
	}
	if got, ok := broadcasting["last_broadcast_time"].(float64); !ok || got != 1700000000.25 {
		t.Fatalf("status_broadcasting.last_broadcast_time = %v (%T), want 1700000000.25", broadcasting["last_broadcast_time"], broadcasting["last_broadcast_time"])
	}
}

func TestHealthStatusBroadcastingWithoutLastStatus(t *testing.T) {
	restore := swapHealthStatusProvider(fakeHealthStatusProvider{clients: 0})
	defer restore()

	broadcasting, ok := doHealthRequest(t)["status_broadcasting"].(map[string]any)
	if !ok {
		t.Fatal("status_broadcasting is not an object")
	}
	if broadcasting["last_broadcast"] != nil {
		t.Fatalf("last_broadcast = %v, want null", broadcasting["last_broadcast"])
	}
	if broadcasting["last_broadcast_time"] != nil {
		t.Fatalf("last_broadcast_time = %v, want null", broadcasting["last_broadcast_time"])
	}
}

func TestHealthPayloadWithoutProvider(t *testing.T) {
	restore := swapHealthStatusProvider(nil)
	defer restore()

	body := doHealthRequest(t)

	assertHealthKeys(t, body, "status", "timestamp", "server", "version", "auth_enabled", "connections", "status_broadcasting")

	connections, ok := body["connections"].(map[string]any)
	if !ok {
		t.Fatalf("connections = %v (%T), want object", body["connections"], body["connections"])
	}
	if _, ok := connections["error"].(string); !ok {
		t.Fatalf("connections.error = %v (%T), want string", connections["error"], connections["error"])
	}

	broadcasting, ok := body["status_broadcasting"].(map[string]any)
	if !ok {
		t.Fatalf("status_broadcasting = %v (%T), want object", body["status_broadcasting"], body["status_broadcasting"])
	}
	if got, ok := broadcasting["active"].(bool); !ok || got {
		t.Fatalf("status_broadcasting.active = %v (%T), want false", broadcasting["active"], broadcasting["active"])
	}
	if _, ok := broadcasting["error"].(string); !ok {
		t.Fatalf("status_broadcasting.error = %v (%T), want string", broadcasting["error"], broadcasting["error"])
	}
}

func TestHealthAuthEnabled(t *testing.T) {
	restore := swapHealthStatusProvider(nil)
	defer restore()

	t.Setenv("AUTH_ENABLED", "yes")
	if got := doHealthRequest(t)["auth_enabled"]; got != true {
		t.Fatalf("AUTH_ENABLED=yes -> auth_enabled = %v, want true", got)
	}

	t.Setenv("AUTH_ENABLED", "off")
	if got := doHealthRequest(t)["auth_enabled"]; got != false {
		t.Fatalf("AUTH_ENABLED=off -> auth_enabled = %v, want false", got)
	}
}
