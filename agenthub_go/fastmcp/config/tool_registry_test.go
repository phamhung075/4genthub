package config_test

import (
	"testing"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

type call struct {
	description string
	fn          any
}

type fakeServer struct{ calls []call }

func (s *fakeServer) Tool(description string) func(any) any {
	return func(fn any) any {
		s.calls = append(s.calls, call{description: description, fn: fn})
		return fn
	}
}

func toolMap(tools ...string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for _, name := range tools {
		fn := func() {}
		m.Set(name, fn)
	}
	return m
}

func TestToolRegistryMounting(t *testing.T) {
	const yaml = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      validate_token:
        enabled: true
        description: "Validate authentication tokens"
        dependencies: ["auth_middleware"]
      disabled_tool:
        enabled: false
      dep_missing:
        enabled: true
        dependencies: ["missing_dep"]
  connection:
    enabled: true
    tools:
      manage_connection:
        enabled: true
global:
  log_tool_registration: true
mounting:
  log_skipped_tools: true
`
	loader := config.NewToolConfigLoader(writeFile(t, "c.yaml", yaml), envFn(map[string]string{"AUTH_ENABLED": "true"}))
	if _, err := loader.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	reg := config.NewToolRegistry(loader)
	reg.RegisterToolGroup("authentication", toolMap("validate_token", "disabled_tool", "dep_missing"))
	reg.RegisterToolGroup("connection", toolMap("manage_connection"))
	reg.AddDependency("auth_middleware")

	server := &fakeServer{}
	stats, err := reg.MountToolsToServer(server)
	if err != nil {
		t.Fatal(err)
	}
	if statsInt(t, stats, "total_groups") != 2 || statsInt(t, stats, "total_tools") != 4 ||
		statsInt(t, stats, "mounted_tools") != 2 || statsInt(t, stats, "disabled_tools") != 1 ||
		statsInt(t, stats, "dependency_failures") != 1 || statsInt(t, stats, "skipped_tools") != 0 {
		t.Fatalf("unexpected stats: %v", stats)
	}
	results := get(t, stats, "results").(cmap)
	authResults, _ := results.Get("authentication")
	if got := get(t, authResults, "enabled"); !eqStrings(got, []string{"validate_token"}) {
		t.Fatalf("enabled = %v", got)
	}
	if got := get(t, authResults, "disabled"); !eqStrings(got, []string{"disabled_tool"}) {
		t.Fatalf("disabled = %v", got)
	}
	if got := get(t, authResults, "dependency_failures"); !eqStrings(got, []string{"dep_missing"}) {
		t.Fatalf("dependency_failures = %v", got)
	}
	if got := get(t, authResults, "skipped"); !eqStrings(got, []string{}) {
		t.Fatalf("skipped = %v", got)
	}

	if len(server.calls) != 2 {
		t.Fatalf("server calls = %v", server.calls)
	}
	if server.calls[0].description != "Validate authentication tokens" {
		t.Fatalf("auth description = %q", server.calls[0].description)
	}
	// The authentication config has no manage_connection entry, so the default is used.
	if server.calls[1].description != "MCP tool: manage_connection" {
		t.Fatalf("connection description = %q", server.calls[1].description)
	}
}

func TestToolRegistrySummaryAndInfo(t *testing.T) {
	const yaml = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      validate_token:
        enabled: true
        description: "Validate authentication tokens"
        dependencies: ["auth_middleware"]
        deprecated: true
        deprecation_message: "use /api/v2/tokens"
      disabled_tool:
        enabled: false
      dep_missing:
        enabled: true
`
	loader := config.NewToolConfigLoader(writeFile(t, "c.yaml", yaml), envFn(map[string]string{"AUTH_ENABLED": "true"}))
	if _, err := loader.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	reg := config.NewToolRegistry(loader)
	reg.RegisterToolGroup("authentication", toolMap("validate_token", "disabled_tool", "dep_missing"))

	summary, err := reg.GetEnabledToolsSummary()
	if err != nil {
		t.Fatal(err)
	}
	entryAny, _ := summary.Get("authentication")
	entry := entryAny.(cmap)
	if got := get(t, entry, "total_tools"); got != 3 {
		t.Fatalf("total_tools = %v", got)
	}
	if got := get(t, entry, "enabled_count"); got != 2 {
		t.Fatalf("enabled_count = %v", got)
	}
	if got := get(t, entry, "enabled_tools"); !eqStrings(got, []string{"validate_token", "dep_missing"}) {
		t.Fatalf("enabled_tools = %v", got)
	}

	on, err := reg.IsGroupEnabled("authentication")
	if err != nil || !on {
		t.Fatalf("IsGroupEnabled = %v, %v", on, err)
	}

	info, err := reg.GetToolInfo("authentication", "validate_token")
	if err != nil {
		t.Fatal(err)
	}
	if got := get(t, info, "enabled"); got != true {
		t.Fatalf("enabled = %v", got)
	}
	if got := get(t, info, "dependencies"); !eqStrings(got, []string{"auth_middleware"}) {
		t.Fatalf("dependencies = %v", got)
	}
	if got := get(t, info, "description"); got != "Validate authentication tokens" {
		t.Fatalf("description = %v", got)
	}
	if got := get(t, info, "deprecated"); got != true {
		t.Fatalf("deprecated = %v", got)
	}
	if got := get(t, info, "deprecation_message"); got != "use /api/v2/tokens" {
		t.Fatalf("deprecation_message = %v", got)
	}
	if _, ok := get(t, info, "config").(cmap); !ok {
		t.Fatalf("config = %T", get(t, info, "config"))
	}
}

func statsInt(t *testing.T, m cmap, key string) int {
	t.Helper()
	v, _ := m.Get(key)
	n, ok := v.(int)
	if !ok {
		t.Fatalf("%s = %v (%T)", key, v, v)
	}
	return n
}

func eqStrings(v any, want []string) bool {
	var list []string
	switch x := v.(type) {
	case []string:
		list = x
	case []any:
		for _, e := range x {
			s, ok := e.(string)
			if !ok {
				return false
			}
			list = append(list, s)
		}
	default:
		return false
	}
	if len(list) != len(want) {
		return false
	}
	for i := range list {
		if list[i] != want[i] {
			return false
		}
	}
	return true
}
