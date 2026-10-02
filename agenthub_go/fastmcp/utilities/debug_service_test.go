package utilities

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestNewDebugServiceReadsFlags(t *testing.T) {
	t.Setenv("DEBUG_SERVICE_ENABLED", "TRUE")
	t.Setenv("DEBUG_HTTP_REQUESTS", "true")
	t.Setenv("DEBUG_API_V2", "false")
	t.Setenv("DEBUG_MCP_TOOLS", "True")
	t.Setenv("DEBUG_AUTHENTICATION", "1")
	t.Setenv("DEBUG_DATABASE", "true")
	t.Setenv("DEBUG_FRONTEND_ISSUES", "true")
	t.Setenv("DEBUG_VERBOSE", "true")
	t.Setenv("DEBUG_STACK_TRACES", " true ")

	d := NewDebugService()
	if !d.DebugEnabled || !d.DebugHTTP || !d.DebugMCP || !d.DebugDatabase || !d.DebugFrontend || !d.DebugVerbose {
		t.Fatalf("flags parsed wrong: %+v", d)
	}
	// .lower() == "true" is exact: "1" and " true " are false.
	if d.DebugAPIV2 || d.DebugAuth || d.DebugStackTraces {
		t.Fatalf("flags parsed wrong: %+v", d)
	}
}

func TestDebugServiceIsEnabled(t *testing.T) {
	off := NewDebugService()
	if off.IsEnabled("general") {
		t.Fatal("disabled service must report false")
	}
	on := &DebugService{DebugEnabled: true, DebugHTTP: true}
	if !on.IsEnabled("general") || !on.IsEnabled("http") {
		t.Fatal("general/http should be enabled")
	}
	if on.IsEnabled("auth") {
		t.Fatal("auth flag is off")
	}
	if on.IsEnabled("unknown") {
		t.Fatal("unknown category must be false")
	}
}

func TestDebugServiceGetDebugStatus(t *testing.T) {
	d := &DebugService{DebugEnabled: true, DebugHTTP: true, DebugVerbose: true}
	status := d.GetDebugStatus()
	if got := status.Keys(); !reflect.DeepEqual(got, []string{"debug_enabled", "categories", "options"}) {
		t.Fatalf("status keys = %v", got)
	}
	categories, _ := status.Get("categories")
	if got := categories.(*entities.OrderedMap[any]).Keys(); !reflect.DeepEqual(got, []string{"http", "api_v2", "mcp", "auth", "database", "frontend"}) {
		t.Fatalf("category keys = %v", got)
	}
	options, _ := status.Get("options")
	if got := options.(*entities.OrderedMap[any]).Keys(); !reflect.DeepEqual(got, []string{"verbose", "stack_traces"}) {
		t.Fatalf("option keys = %v", got)
	}
}
