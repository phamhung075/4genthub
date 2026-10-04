package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	mcpcontrollers "agenthub/fastmcp/agent_management/interface/mcp_controllers"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// authenticateAgentsTestUser makes currentUser resolve to a valid UUID user so the
// authed handlers run instead of returning 403.
func authenticateAgentsTestUser(t *testing.T) {
	t.Helper()
	previous := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		id := "11111111-1111-4111-8111-111111111111"
		return &authdomain.User{ID: &id, Email: "dev@example.com", Username: "dev"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })
}

func agentsTestMux(t *testing.T) *http.ServeMux {
	t.Helper()
	mux := http.NewServeMux()
	mountAgentsRoutes(mux, nil)
	return mux
}

func doAgentsRequest(t *testing.T, mux *http.ServeMux, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// TestMountAgentsRoutesRegistersEveryPattern checks the pattern is served
// (a registered authed route answers 403 without a bearer, never 404).
func TestMountAgentsRoutesRegistersEveryPattern(t *testing.T) {
	mux := http.NewServeMux()
	mountAgentsRoutes(mux, nil)
	probes := []struct{ method, path string }{
		{http.MethodPost, "/api/v2/agents/call"},
	}
	for _, p := range probes {
		req := httptest.NewRequest(p.method, p.path, nil)
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code == http.StatusNotFound {
			t.Errorf("%s %s: not registered (got 404)", p.method, p.path)
		}
	}
}

// TestAgentsAssignmentRoutesAreNotServed checks the assignment endpoints stay deleted: the
// controller has no assignment methods, so serving them would only fake a 500.
func TestAgentsAssignmentRoutesAreNotServed(t *testing.T) {
	authenticateAgentsTestUser(t)
	mux := agentsTestMux(t)
	for _, c := range []struct{ method, path string }{
		{http.MethodPost, "/api/v2/agents/assign?branch_id=b1&agent_id=a1"},
		{http.MethodDelete, "/api/v2/agents/unassign/b1"},
		{http.MethodGet, "/api/v2/agents/branch/b1/assignment"},
		{http.MethodGet, "/api/v2/agents/project/p1/assignments"},
	} {
		if rec := doAgentsRequest(t, mux, c.method, c.path, ""); rec.Code != http.StatusNotFound && rec.Code != http.StatusMethodNotAllowed {
			t.Errorf("%s %s: status = %d, want 404 or 405", c.method, c.path, rec.Code)
		}
	}
}

// TestAgentsCallRequiresAgentName checks POST /call's 400.
func TestAgentsCallRequiresAgentName(t *testing.T) {
	authenticateAgentsTestUser(t)
	mux := agentsTestMux(t)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/agents/call", `{"params":{}}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "agent_name is required") {
		t.Fatalf("body = %s", rec.Body.String())
	}
}

type fakeAgentConfigProvider struct {
	config *entities.OrderedMap[any]
	err    error
}

func (f fakeAgentConfigProvider) GetAgentForCall(context.Context, *amvo.UserId, string) (*entities.OrderedMap[any], error) {
	return f.config, f.err
}

func withCallAgentProvider(t *testing.T, provider mcpcontrollers.AgentConfigProvider, err error) {
	t.Helper()
	previous := newCallAgentProvider
	newCallAgentProvider = func(*database.SessionManager) (mcpcontrollers.AgentConfigProvider, error) {
		return provider, err
	}
	t.Cleanup(func() { newCallAgentProvider = previous })
}

// TestAgentsCallSuccess checks the success body (success/agent/source/called_by).
func TestAgentsCallSuccess(t *testing.T) {
	authenticateAgentsTestUser(t)
	config := entities.NewOrderedMap[any]()
	config.Set("name", "Coding Agent")
	config.Set("slug", "coding-agent")
	withCallAgentProvider(t, fakeAgentConfigProvider{config: config}, nil)

	mux := agentsTestMux(t)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/agents/call", `{"agent_name":"coding-agent"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", rec.Code, rec.Body.String())
	}
	var got map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if got["success"] != true {
		t.Errorf("success = %v, want true", got["success"])
	}
	if got["source"] != "agent-management-system" {
		t.Errorf("source = %v", got["source"])
	}
	if got["called_by"] != "dev@example.com" {
		t.Errorf("called_by = %v", got["called_by"])
	}
	if got["agent"] == nil {
		t.Errorf("agent = nil, want the facade config")
	}
}

// TestAgentsCallNotFound checks a missing template maps to 404.
func TestAgentsCallNotFound(t *testing.T) {
	authenticateAgentsTestUser(t)
	withCallAgentProvider(t, fakeAgentConfigProvider{err: tmvo.ValueErrorf("Agent template not found: ghost")}, nil)

	mux := agentsTestMux(t)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/agents/call", `{"agent_name":"ghost"}`)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404 (body %s)", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "Agent not found: ghost") {
		t.Fatalf("body = %s", rec.Body.String())
	}
}

// TestAgentsCallGenericFailure checks the except Exception branch keeps status 200
// with the Python body shape.
func TestAgentsCallGenericFailure(t *testing.T) {
	authenticateAgentsTestUser(t)
	withCallAgentProvider(t, nil, errors.New("database down"))

	mux := agentsTestMux(t)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/agents/call", `{"agent_name":"coding-agent"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", rec.Code, rec.Body.String())
	}
	var got map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if got["success"] != false || got["message"] != "Failed to call agent" {
		t.Errorf("body = %v", got)
	}
	if got["error"] != "database down" {
		t.Errorf("error = %v, want database down", got["error"])
	}
	if _, ok := got["traceback"]; !ok {
		t.Errorf("traceback missing from %v", got)
	}
}

// TestAgentsCallInvalidUserID checks a non-UUID user id keeps Python's ValueError
// -> 404 path before the facade is built.
func TestAgentsCallInvalidUserID(t *testing.T) {
	previous := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		id := "dev-user-001"
		return &authdomain.User{ID: &id, Email: "dev@example.com"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })

	mux := agentsTestMux(t)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/agents/call", `{"agent_name":"coding-agent"}`)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404 (body %s)", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "Agent not found: coding-agent") {
		t.Fatalf("body = %s", rec.Body.String())
	}
}
