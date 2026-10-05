package httpapp

import (
	"reflect"
	"testing"
)

// TestConnectionToolDefinition checks manage_connection is listed exactly as the
// Python controller publishes it (connection_mcp_controller.py:47):
// description "Basic health check endpoint for system monitoring" and the
// inputSchema FastMCP derives from
// manage_connection(include_details: bool = True, user_id: str | None = None).
func TestConnectionToolDefinition(t *testing.T) {
	def, err := connectionToolDefinition()
	if err != nil {
		t.Fatalf("connectionToolDefinition: %v", err)
	}

	if got, want := def["name"], "manage_connection"; got != want {
		t.Fatalf("name = %v, want %q", got, want)
	}
	if got, want := def["description"], "Basic health check endpoint for system monitoring"; got != want {
		t.Fatalf("description = %v, want %q", got, want)
	}

	wantSchema := map[string]any{
		"properties": map[string]any{
			"include_details": map[string]any{
				"default":     true,
				"description": "Whether to include detailed information in health response",
				"title":       "Include Details",
				"type":        "boolean",
			},
			"user_id": map[string]any{
				"anyOf": []any{
					map[string]any{"type": "string"},
					map[string]any{"type": "null"},
				},
				"default":     nil,
				"description": "User identifier for authentication and audit trails",
				"title":       "User Id",
			},
		},
		"type": "object",
	}
	if !reflect.DeepEqual(def["inputSchema"], wantSchema) {
		t.Fatalf("inputSchema = %#v, want %#v", def["inputSchema"], wantSchema)
	}
}

// TestCallManageConnection checks the connection controller returns the health
// check mapping the MCP dispatcher serializes (a success/status response).
func TestCallManageConnection(t *testing.T) {
	app := &App{}

	result := app.callManageConnection(map[string]any{"include_details": false}, nil)

	plain, err := plainJSON(result)
	if err != nil {
		t.Fatalf("plainJSON(result): %v", err)
	}
	resp, ok := plain.(map[string]any)
	if !ok {
		t.Fatalf("result = %T, want a JSON object", plain)
	}
	if _, ok := resp["success"]; !ok {
		t.Fatalf("result %v is missing the success key", resp)
	}
	if _, ok := resp["status"]; !ok {
		t.Fatalf("result %v is missing the status key", resp)
	}
}
