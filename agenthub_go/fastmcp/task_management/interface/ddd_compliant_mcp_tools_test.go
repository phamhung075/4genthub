package interfacelayer

import (
	"encoding/json"
	"os"
	"reflect"

	"agenthub/fastmcp/task_management/domain/value_objects"
	"context"
	"testing"

	authmw "agenthub/fastmcp/auth/middleware"
	"agenthub/fastmcp/task_management/application/services"
	branchctl "agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller"
)

type recordingServer struct{ names []string }

func (r *recordingServer) Tool(name, _ string, _ any) { r.names = append(r.names, name) }

func TestNewDDDCompliantMCPToolsRegistersTools(t *testing.T) {
	fs := services.NewFacadeService(nil, nil, nil, nil, nil, nil)
	tools, err := NewDDDCompliantMCPTools(Dependencies{FacadeService: fs}, nil)
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]bool{"manage_task": true, "manage_subtask": true, "manage_project": true, "manage_git_branch": true}
	for _, d := range tools.ToolDefinitions() {
		if d.Handler == nil || d.Parameters == nil {
			t.Errorf("%s: missing handler or schema", d.Name)
		}
		delete(want, d.Name)
	}
	for n := range want {
		t.Errorf("tool %s not defined", n)
	}
	srv := &recordingServer{}
	tools.RegisterTools(srv)
	if len(srv.names) == 0 {
		t.Fatal("nothing registered")
	}
}

func TestAuthHooksReadRequestContext(t *testing.T) {
	wireAuthHooks()
	if got := branchctl.GetCurrentUserIDHook(context.Background()); got != nil {
		t.Fatalf("no user in ctx should be nil, got %v", got)
	}
	_ = authmw.GetCurrentUserID
}

func TestNewDDDCompliantMCPToolsRequiresFacadeService(t *testing.T) {
	services.SetInstance(nil)
	if _, err := NewDDDCompliantMCPTools(Dependencies{}, nil); err == nil {
		t.Fatal("expected error without a FacadeService")
	}
}

// TestToolDefinitionsMatchPythonToolRegistry compares each tool's description and
// inputSchema with the registry real FastMCP produces for the Python tools
// (testdata/tools_golden.json, generated from the Python server).
func TestToolDefinitionsMatchPythonToolRegistry(t *testing.T) {
	raw, err := os.ReadFile("testdata/tools_golden.json")
	if err != nil {
		t.Fatal(err)
	}
	var golden map[string]struct {
		Description string `json:"description"`
		Parameters  any    `json:"parameters"`
	}
	if err := json.Unmarshal(raw, &golden); err != nil {
		t.Fatal(err)
	}
	fs := services.NewFacadeService(nil, nil, nil, nil, nil, nil)
	tools, err := NewDDDCompliantMCPTools(Dependencies{FacadeService: fs, DatabaseAvailable: true}, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, d := range tools.ToolDefinitions() {
		want, ok := golden[d.Name]
		if !ok {
			t.Errorf("%s not in golden", d.Name)
			continue
		}
		if d.Description != want.Description {
			t.Errorf("%s: description differs", d.Name)
		}
		js, err := value_objects.PyJSONDumpsCompact(d.Parameters)
		if err != nil {
			t.Fatal(err)
		}
		var got any
		if err := json.Unmarshal([]byte(js), &got); err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(got, want.Parameters) {
			t.Errorf("%s: inputSchema differs\n got %s", d.Name, js)
		}
	}
}
