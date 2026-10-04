package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/application/services"
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
