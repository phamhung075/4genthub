package routes

import (
	"encoding/json"
	"strings"
	"testing"

	"agenthub/fastmcp/config"
	dtos "agenthub/fastmcp/connection_management/application/dtos"
)

// TestHealthCheckRecoverBranchProducesWellFormedResponse drives HealthCheck into
// its panic/recover branch and asserts the recovery response is well formed and
// advertises the shared config.ServerName constant, so the naming edit can never
// break recovery itself.
func TestHealthCheckRecoverBranchProducesWellFormedResponse(t *testing.T) {
	orig := healthCheckFn
	healthCheckFn = func(*bool, *string) *dtos.HealthCheckResponse {
		panic("health probe exploded")
	}
	t.Cleanup(func() { healthCheckFn = orig })

	out := HealthCheck(nil)
	if out == nil {
		t.Fatal("HealthCheck returned nil after recovering")
	}

	wantKeys := []string{"success", "status", "server_name", "version", "uptime_seconds", "timestamp", "error"}
	if got := strings.Join(out.Keys(), ","); got != strings.Join(wantKeys, ",") {
		t.Fatalf("recovery key order = %q, want %q", got, strings.Join(wantKeys, ","))
	}

	if v, _ := out.Get("success"); v != true {
		t.Errorf("success = %v, want true", v)
	}
	if v, _ := out.Get("status"); v != "healthy" {
		t.Errorf("status = %v, want healthy", v)
	}
	if v, _ := out.Get("server_name"); v != config.ServerName {
		t.Errorf("server_name = %v, want %v", v, config.ServerName)
	}

	// The body must remain serializable and expose the same name on the wire.
	body := map[string]any{}
	for _, k := range out.Keys() {
		v, _ := out.Get(k)
		body[k] = v
	}
	raw, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("recovery response is not JSON-serializable: %v", err)
	}
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("recovery response is not valid JSON: %v", err)
	}
	if decoded["server_name"] != config.ServerName {
		t.Errorf("wire server_name = %v, want %v", decoded["server_name"], config.ServerName)
	}
	if msg, _ := decoded["error"].(string); !strings.Contains(msg, "health probe exploded") {
		t.Errorf("recovery error = %q, want it to mention the recovered panic", msg)
	}
}
