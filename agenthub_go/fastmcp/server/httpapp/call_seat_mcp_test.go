package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/infrastructure/database"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// stubCallSeatResolver stands in for SeatResolutionService. call_seat must publish and
// dispatch without a database, and the resolver is the only seam it needs.
type stubCallSeatResolver struct{ resolved *repositories.ResolvedSeat }

func (s stubCallSeatResolver) ResolveSeat(_ context.Context, _, roomSlug, _ string) (*repositories.ResolvedSeat, error) {
	if roomSlug == "ghost" {
		return nil, errors.New("room ghost not found")
	}
	return s.resolved, nil
}

func newCallSeatTestApp(t *testing.T, resolved *repositories.ResolvedSeat) *App {
	t.Helper()
	controller := seatcontrollers.NewCallSeatController(stubSeatAuth{}, stubCallSeatResolver{resolved: resolved})
	tools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     services.NewFacadeService(nil, nil, nil, nil, nil, nil, nil),
		DatabaseAvailable: true,
		CallSeat:          controller,
	}, nil)
	if err != nil {
		t.Fatalf("NewDDDCompliantMCPTools: %v", err)
	}
	return &App{mcpTools: tools}
}

func TestMCPToolsListPublishesCallSeat(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	rec := postMCP(t, newCallSeatTestApp(t, &repositories.ResolvedSeat{}), `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	var wire struct {
		Result struct {
			Tools []struct {
				Name        string `json:"name"`
				Description string `json:"description"`
				InputSchema struct {
					Type       string                    `json:"type"`
					Required   []string                  `json:"required"`
					Properties map[string]map[string]any `json:"properties"`
				} `json:"inputSchema"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode tools/list: %v", err)
	}
	for _, tool := range wire.Result.Tools {
		if tool.Name == "call_agent" {
			t.Fatal("tools/list still publishes the removed call_agent tool")
		}
	}
	for _, tool := range wire.Result.Tools {
		if tool.Name != "call_seat" {
			continue
		}
		if tool.Description != seatcontrollers.CallSeatToolDescription {
			t.Errorf("description = %q", tool.Description)
		}
		schema := tool.InputSchema
		if schema.Type != "object" || len(schema.Required) != 2 || schema.Required[0] != "room" || schema.Required[1] != "seat" {
			t.Errorf("schema = %+v", schema)
		}
		for _, name := range []string{"room", "seat", "user_id"} {
			if schema.Properties[name]["type"] != "string" {
				t.Errorf("property %s = %v", name, schema.Properties[name])
			}
		}
		return
	}
	t.Fatalf("tools/list does not publish call_seat: %s", rec.Body.String())
}

func TestMCPCallSeatResolvesASeat(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	resolved := &repositories.ResolvedSeat{
		Hash:    "abc123",
		Runtime: "omp",
		Files:   []repositories.ResolvedFile{{Path: "guidance/role.md", Content: "You are the lead."}},
	}
	app := newCallSeatTestApp(t, resolved)

	payload := `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"call_seat","arguments":{"room":"4genthub-dev","seat":"lead"}}}`
	rec := postMCP(t, app, payload, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			IsError bool `json:"isError"`
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil || wire.Result.IsError || len(wire.Result.Content) != 1 {
		t.Fatalf("decode tools/call: %v %s", err, rec.Body.String())
	}
	var result struct {
		Success bool             `json:"success"`
		Room    string           `json:"room"`
		Seat    string           `json:"seat"`
		Hash    string           `json:"hash"`
		Runtime string           `json:"runtime"`
		Files   []map[string]any `json:"files"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if !result.Success || result.Room != "4genthub-dev" || result.Seat != "lead" || result.Hash != "abc123" || result.Runtime != "omp" {
		t.Errorf("result = %+v", result)
	}
	if len(result.Files) != 1 || result.Files[0]["path"] != "guidance/role.md" {
		t.Errorf("files = %+v", result.Files)
	}
}

func TestMCPCallSeatReportsAResolverFailure(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newCallSeatTestApp(t, &repositories.ResolvedSeat{})

	payload := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"call_seat","arguments":{"room":"ghost","seat":"lead"}}}`
	rec := postMCP(t, app, payload, "")
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil || len(wire.Result.Content) != 1 {
		t.Fatalf("decode tools/call: %v %s", err, rec.Body.String())
	}
	var result struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if result.Success || result.Error != "room ghost not found" {
		t.Errorf("result = %+v", result)
	}
}

// The call_seat resolver takes its MCP URL from the request origin dispatchMCPTool put on
// ctx, so a self-hosted stack with no AGENTHUB_PUBLIC_URL renders the caller's own URL.
func TestCallSeatWiringDerivesMCPURLFromRequestContext(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mcpURL := capturedCallSeatMCPURL(t, authedMCPRequest("internal:8000", map[string]string{
		"X-Forwarded-Proto": "https",
		"X-Forwarded-Host":  "mcp.example.test, internal",
	}))

	if mcpURL != "https://mcp.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the forwarded request origin", mcpURL)
	}
}

// A pinned AGENTHUB_PUBLIC_URL still wins over the request the tool call arrived on.
func TestCallSeatWiringPinnedURLWinsOverRequestContext(t *testing.T) {
	t.Setenv(publicURLEnv, "https://pinned.example.test/")
	mcpURL := capturedCallSeatMCPURL(t, authedMCPRequest("internal:8000", nil))

	if mcpURL != "https://pinned.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the pinned override", mcpURL)
	}
}

// capturedCallSeatMCPURL runs one successful call_seat through newCallSeatController with
// newSeatSource stubbed, and returns the MCP URL the resolver built the source with.
func capturedCallSeatMCPURL(t *testing.T, req *http.Request) string {
	t.Helper()
	var mcpURL string
	previous := newSeatSource
	newSeatSource = func(_ *database.SessionManager, u string) (seatSource, error) {
		mcpURL = u
		return &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc123", Runtime: "omp"}}, nil
	}
	t.Cleanup(func() { newSeatSource = previous })

	uid := "11111111-1111-4111-8111-111111111111"
	room, seat := "dev", "coder"
	result := newCallSeatController(nil).CallSeat(withRequestPublicOrigin(context.Background(), req), &room, &seat, &uid)
	if success, _ := result.Get("success"); success != true {
		t.Fatalf("call_seat failed: %v", result)
	}
	return mcpURL
}

func authedMCPRequest(host string, headers map[string]string) *http.Request {
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	if host != "" {
		req.Host = host
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	return req
}
