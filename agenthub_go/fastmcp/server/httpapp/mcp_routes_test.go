package httpapp

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/services"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// toolsGoldenPath is interface/testdata/tools_golden.json, the registry real
// FastMCP publishes for the Python tools.
const toolsGoldenPath = "../../task_management/interface/testdata/tools_golden.json"

// newMCPTestApp builds an App with the real MCP tool registry. The controllers
// do not reach the database while only listing tools, so no SessionManager is
// needed.
func newMCPTestApp(t *testing.T) *App {
	t.Helper()
	fs := services.NewFacadeService(nil, nil, nil, nil, nil, nil, nil)
	tools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     fs,
		DatabaseAvailable: true,
	}, nil)
	if err != nil {
		t.Fatalf("NewDDDCompliantMCPTools: %v", err)
	}
	return &App{mcpTools: tools}
}

// postMCP sends a raw JSON-RPC body through the registered POST /mcp route.
func postMCP(t *testing.T, app *App, payload, authorization string) *httptest.ResponseRecorder {
	t.Helper()
	mux := http.NewServeMux()
	app.registerMCPRoutes(mux)
	req := httptest.NewRequest(http.MethodPost, "/mcp", strings.NewReader(payload))
	if authorization != "" {
		req.Header.Set("Authorization", authorization)
	}
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// TestMCPToolsListMatchesGolden compares the wire tools/list result with
// tools_golden.json (the Python registry: name -> description + parameters).
func TestMCPToolsListMatchesGolden(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}

	var wire struct {
		Result struct {
			Tools []struct {
				Name        string          `json:"name"`
				Description string          `json:"description"`
				InputSchema json.RawMessage `json:"inputSchema"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode response: %v", err)
	}

	// manage_connection is registered by mcp_entry_point.py (register_ddd_connection_tools),
	// and manage_seat and call_seat exist only in Go; all three are outside the Python
	// registry the golden file was generated from (the seat tools are covered by
	// TestMCPManageSeat* and TestMCPCallSeat*).
	got := make(map[string]any, len(wire.Result.Tools))
	sawConnection := false
	for _, tool := range wire.Result.Tools {
		if tool.Name == "manage_connection" {
			sawConnection = true
			continue
		}
		if tool.Name == "manage_seat" || tool.Name == "call_seat" {
			continue
		}
		var schema any
		if err := json.Unmarshal(tool.InputSchema, &schema); err != nil {
			t.Fatalf("%s: decode inputSchema: %v", tool.Name, err)
		}
		if _, dup := got[tool.Name]; dup {
			t.Fatalf("duplicate tool %s", tool.Name)
		}
		got[tool.Name] = map[string]any{
			"description": tool.Description,
			"parameters":  schema,
		}
	}

	if !sawConnection {
		t.Fatal("tools/list does not publish manage_connection")
	}

	raw, err := os.ReadFile(toolsGoldenPath)
	if err != nil {
		t.Fatalf("read golden: %v", err)
	}
	var golden map[string]any
	if err := json.Unmarshal(raw, &golden); err != nil {
		t.Fatalf("decode golden: %v", err)
	}

	if !reflect.DeepEqual(got, golden) {
		gotJSON, _ := json.MarshalIndent(got, "", " ")
		t.Fatalf("tools/list does not match tools_golden.json\n got: %s", gotJSON)
	}
}

// TestMCPToolsCallSerializesResult checks tools/call puts a non-empty,
// well-formed JSON tool result in result.content[0].text.
func TestMCPToolsCallSerializesResult(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	for _, name := range []string{"get_mcp_status", "check_session_health", "manage_agent"} {
		t.Run(name, func(t *testing.T) {
			payload := fmt.Sprintf(`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":%q,"arguments":{}}}`, name)
			rec := postMCP(t, app, payload, "")
			if rec.Code != http.StatusOK {
				t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
			}

			var wire struct {
				Result struct {
					Content []struct {
						Type string `json:"type"`
						Text string `json:"text"`
					} `json:"content"`
					IsError bool `json:"isError"`
				} `json:"result"`
			}
			if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
				t.Fatalf("decode response: %v", err)
			}
			if len(wire.Result.Content) != 1 {
				t.Fatalf("content length = %d, want 1", len(wire.Result.Content))
			}
			if wire.Result.Content[0].Type != "text" {
				t.Fatalf("content[0].type = %q, want text", wire.Result.Content[0].Type)
			}
			text := wire.Result.Content[0].Text
			if text == "" {
				t.Fatal("content[0].text is empty")
			}
			if !json.Valid([]byte(text)) {
				t.Fatalf("content[0].text is not valid JSON: %q", text)
			}
		})
	}
}

// TestMCPResourcesAndPromptsLists checks the empty MCP list shapes.
func TestMCPResourcesAndPromptsLists(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	for _, tc := range []struct{ method, field string }{
		{"resources/list", "resources"},
		{"prompts/list", "prompts"},
	} {
		rec := postMCP(t, app, fmt.Sprintf(`{"jsonrpc":"2.0","id":1,"method":%q}`, tc.method), "")
		if rec.Code != http.StatusOK {
			t.Fatalf("%s: status = %d, want 200", tc.method, rec.Code)
		}
		var wire struct {
			Result map[string]json.RawMessage `json:"result"`
		}
		if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
			t.Fatalf("%s: decode response: %v", tc.method, err)
		}
		raw, ok := wire.Result[tc.field]
		if !ok {
			t.Fatalf("%s: result missing %q", tc.method, tc.field)
		}
		var list []any
		if err := json.Unmarshal(raw, &list); err != nil {
			t.Fatalf("%s: %q is not a list: %v", tc.method, tc.field, err)
		}
		if len(list) != 0 {
			t.Fatalf("%s: %q = %v, want an empty list", tc.method, tc.field, list)
		}
	}
}

// TestMCPInitializeAndToolsListRequireBearerWhenAuthEnabled checks the protected
// methods reject a missing or invalid bearer token when AUTH_ENABLED=true.
func TestMCPInitializeAndToolsListRequireBearerWhenAuthEnabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")

	token := wsTestToken(t, []string{"read"})

	app := newMCPTestApp(t)

	for _, method := range []string{"initialize", "tools/list"} {
		rec := postMCP(t, app, fmt.Sprintf(`{"jsonrpc":"2.0","id":1,"method":%q}`, method), "")
		if rec.Code != http.StatusForbidden {
			t.Errorf("%s without bearer: status = %d, want 403", method, rec.Code)
		}
	}

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "Bearer "+token)
	if rec.Code != http.StatusOK {
		t.Fatalf("tools/list with a valid bearer: status = %d, want 200", rec.Code)
	}

	rec = postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"initialize"}`, "Bearer "+token+"x")
	if rec.Code == http.StatusOK {
		t.Fatal("initialize with an invalid bearer: status = 200, want an authentication error")
	}
}

// Every tool tools/list publishes must be dispatchable: a name missing from
// dispatchMCPTool answers "Unknown tool" (the manage_connection gap).
func TestMCPEveryListedToolIsDispatchable(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	var list struct {
		Result struct {
			Tools []struct {
				Name string `json:"name"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("decode tools/list: %v", err)
	}
	if len(list.Result.Tools) == 0 {
		t.Fatal("tools/list is empty")
	}
	for _, tool := range list.Result.Tools {
		payload := `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"` + tool.Name + `","arguments":{}}}`
		body := postMCP(t, app, payload, "").Body.String()
		if strings.Contains(body, "Unknown tool") {
			t.Errorf("%s is listed by tools/list but tools/call answers Unknown tool: %s", tool.Name, body)
		}
	}
}
