package httpapp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/server/metrics"
)

// miscMux mounts the misc routes on a fresh mux, giving each test its own
// registration store (mountMiscRoutes creates one per call).
func miscMux() *http.ServeMux {
	mux := http.NewServeMux()
	mountMiscRoutes(mux)
	return mux
}

// miscRequest runs one request and returns the recorder.
func miscRequest(mux *http.ServeMux, method, path, body, contentType string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

func miscJSON(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var m map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &m); err != nil {
		t.Fatalf("response is not a JSON object: %v (%s)", err, rec.Body.String())
	}
	return m
}

func TestMiscRegisterResponse(t *testing.T) {
	mux := miscMux()
	rec := miscRequest(mux, http.MethodPost, "/register", `{"client_info":{"name":"c"},"capabilities":{"tools":true}}`, "application/json")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (%s)", rec.Code, rec.Body.String())
	}
	body := miscJSON(t, rec)

	if body["success"] != true {
		t.Errorf("success = %v", body["success"])
	}
	sessionID, _ := body["session_id"].(string)
	if sessionID == "" {
		t.Fatalf("session_id missing: %v", body)
	}
	server, _ := body["server"].(map[string]any)
	if server["name"] != "agenthub-server" || server["version"] != "2.1.0" || server["protocol_version"] != "2025-06-18" {
		t.Errorf("server = %v", server)
	}
	endpoints, _ := body["endpoints"].(map[string]any)
	if endpoints["mcp"] != "http://example.com/mcp/" {
		t.Errorf("endpoints.mcp = %v", endpoints["mcp"])
	}
	if endpoints["initialize"] != "http://example.com/mcp/initialize" || endpoints["tools"] != "http://example.com/mcp/tools/list" || endpoints["health"] != "http://example.com/health" {
		t.Errorf("endpoints = %v", endpoints)
	}
	if body["transport"] != "streamable-http" {
		t.Errorf("transport = %v", body["transport"])
	}
	auth, _ := body["authentication"].(map[string]any)
	if auth["required"] != true || auth["type"] != "Bearer" || auth["header"] != "Authorization" || auth["format"] != "Bearer YOUR_JWT_TOKEN_HERE" {
		t.Errorf("authentication = %v", auth)
	}
	caps, _ := body["capabilities"].(map[string]any)
	for _, k := range []string{"tools", "resources", "prompts", "logging", "progress"} {
		if caps[k] != true {
			t.Errorf("capabilities[%s] = %v", k, caps[k])
		}
	}
	instructions, _ := body["instructions"].(map[string]any)
	if instructions["next_step"] != "Initialize connection at /mcp/initialize endpoint" {
		t.Errorf("instructions = %v", instructions)
	}
}

func TestMiscRegistrationsListAndUnregister(t *testing.T) {
	mux := miscMux()

	var sessionID string
	reg := miscRequest(mux, http.MethodPost, "/register", "{}", "application/json")
	regBody := miscJSON(t, reg)
	sessionID, _ = regBody["session_id"].(string)
	if sessionID == "" {
		t.Fatalf("session_id missing: %v", regBody)
	}

	rec := miscRequest(mux, http.MethodGet, "/registrations", "", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d (%s)", rec.Code, rec.Body.String())
	}
	list := miscJSON(t, rec)
	if list["active_registrations"] != float64(1) {
		t.Errorf("active_registrations = %v", list["active_registrations"])
	}
	sessions, _ := list["sessions"].([]any)
	if len(sessions) != 1 || sessions[0] != sessionID {
		t.Errorf("sessions = %v", sessions)
	}
	details, _ := list["details"].([]any)
	if len(details) != 1 {
		t.Fatalf("details = %v", details)
	}
	detail, _ := details[0].(map[string]any)
	if detail["session_id"] != sessionID {
		t.Errorf("detail.session_id = %v", detail["session_id"])
	}
	if detail["client_ip"] != "192.0.2.1" {
		t.Errorf("detail.client_ip = %v", detail["client_ip"])
	}
	if _, ok := detail["registered_at"].(float64); !ok {
		t.Errorf("detail.registered_at = %v", detail["registered_at"])
	}
	if _, ok := detail["last_activity"].(float64); !ok {
		t.Errorf("detail.last_activity = %v", detail["last_activity"])
	}

	unreg := miscRequest(mux, http.MethodPost, "/unregister", `{"session_id":"`+sessionID+`"}`, "application/json")
	unregBody := miscJSON(t, unreg)
	if unregBody["success"] != true || unregBody["message"] != "Client unregistered successfully" {
		t.Errorf("unregister body = %v", unregBody)
	}

	list = miscJSON(t, miscRequest(mux, http.MethodGet, "/registrations", "", ""))
	if list["active_registrations"] != float64(0) {
		t.Errorf("after unregister active_registrations = %v", list["active_registrations"])
	}
}

func TestMiscUnregisterInvalidSession(t *testing.T) {
	mux := miscMux()
	cases := []struct {
		name string
		body string
		want string
	}{
		{"unknown session", `{"session_id":"nope"}`, "Invalid session"},
		{"missing session", `{}`, "Invalid session"},
		{"null body", `null`, "Unregistration failed"},
		{"empty body", ``, "Unregistration failed"},
		{"non-object body", `[1,2]`, "Unregistration failed"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := miscRequest(mux, http.MethodPost, "/unregister", tc.body, "application/json")
			if rec.Code != http.StatusOK {
				t.Fatalf("status = %d (%s)", rec.Code, rec.Body.String())
			}
			body := miscJSON(t, rec)
			if body["error"] != tc.want {
				t.Errorf("error = %v, want %q", body["error"], tc.want)
			}
			if _, ok := body["message"].(string); !ok {
				t.Errorf("message missing: %v", body)
			}
		})
	}
}

func TestMiscWebSocketMetrics(t *testing.T) {
	metrics.UpdateConnectionCount(7, 5, 2)
	metrics.RecordRetryAttempt(true, 1)

	rec := miscRequest(miscMux(), http.MethodGet, "/ws/metrics", "", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d (%s)", rec.Code, rec.Body.String())
	}
	if got := rec.Header().Get("Content-Type"); got != miscPrometheusContentType {
		t.Errorf("content-type = %q, want %q", got, miscPrometheusContentType)
	}
	text := rec.Body.String()
	for _, want := range []string{
		"# HELP websocket_connections Number of active WebSocket connections",
		"# TYPE websocket_connections gauge",
		`websocket_connections{status="active"} 7.0`,
		`websocket_connections{status="authenticated"} 5.0`,
		"# TYPE websocket_message_retries_total counter",
	} {
		if !strings.Contains(text, want) {
			t.Errorf("metrics missing %q in:\n%s", want, text)
		}
	}
}
