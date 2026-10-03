package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/application/services"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

type stubSeatAuth struct{}

func (stubSeatAuth) GetAuthenticatedUserID(context.Context, *string, string) (string, error) {
	return "user-1", nil
}

func newManageSeatTestApp(t *testing.T, fake *fakeSeatAdmin) *App {
	t.Helper()
	controller := seatcontrollers.NewManageSeatController(stubSeatAuth{}, seatservices.NewSeatAdminService(fake))
	tools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     services.NewFacadeService(nil, nil, nil, nil, nil, nil, nil),
		DatabaseAvailable: true,
		ManageSeat:        controller,
	}, nil)
	if err != nil {
		t.Fatalf("NewDDDCompliantMCPTools: %v", err)
	}
	return &App{mcpTools: tools}
}

func TestMCPToolsListPublishesManageSeat(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	rec := postMCP(t, newManageSeatTestApp(t, newFakeSeatAdmin()), `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
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
		if tool.Name != "manage_seat" {
			continue
		}
		if tool.Description != seatcontrollers.ManageSeatToolDescription {
			t.Errorf("description = %q", tool.Description)
		}
		schema := tool.InputSchema
		if schema.Type != "object" || len(schema.Required) != 1 || schema.Required[0] != "action" {
			t.Errorf("schema = %+v", schema)
		}
		for _, name := range []string{"action", "room", "seat", "runtime", "model", "user_id"} {
			if schema.Properties[name]["type"] != "string" {
				t.Errorf("property %s = %v", name, schema.Properties[name])
			}
		}
		return
	}
	t.Fatalf("tools/list does not publish manage_seat: %s", rec.Body.String())
}

func TestMCPManageSeatSetOccupant(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", Status: "active"})
	app := newManageSeatTestApp(t, fake)

	payload := `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"manage_seat","arguments":{"action":"set_occupant","room":"dev","seat":"alice","runtime":"codex","model":"gpt-5.1"}}}`
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
		Success bool           `json:"success"`
		Seat    map[string]any `json:"seat"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if !result.Success || result.Seat["runtime"] != "codex" || result.Seat["model"] != "gpt-5.1" || result.Seat["room"] != "dev" {
		t.Errorf("result = %+v", result)
	}
	if fake.seats[0].Runtime != "codex" || fake.seats[0].Model != "gpt-5.1" {
		t.Errorf("stored seat = %+v", fake.seats[0])
	}
}
