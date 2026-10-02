package config_test

import (
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

type cmap = *entities.OrderedMap[any]

func envFn(env map[string]string) func(string) (string, bool) {
	return func(k string) (string, bool) { v, ok := env[k]; return v, ok }
}

func writeFile(t *testing.T, name, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), name)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func get(t *testing.T, m any, key string) any {
	t.Helper()
	om, ok := m.(cmap)
	if !ok {
		t.Fatalf("not a map: %T", m)
	}
	v, _ := om.Get(key)
	return v
}

func TestToolConfigLoaderMissingFileKeepsEmptyConfigData(t *testing.T) {
	l := config.NewToolConfigLoader(filepath.Join(t.TempDir(), "missing.yaml"), envFn(nil))
	defaults, err := l.LoadConfig()
	if err != nil {
		t.Fatal(err)
	}
	if got := get(t, defaults, "version"); got != "1.0.0" {
		t.Fatalf("version = %v", got)
	}
	authTools := get(t, get(t, get(t, defaults, "tools"), "authentication"), "tools")
	if got := get(t, get(t, authTools, "generate_token"), "enabled"); got != false {
		t.Fatalf("default generate_token.enabled = %v", got)
	}
	// Python returns the defaults without assigning self.config_data.
	root, ok := l.ConfigData.(cmap)
	if !ok || root.Len() != 0 {
		t.Fatalf("ConfigData should stay empty, got %v", l.ConfigData)
	}
	on, err := l.IsToolEnabled("authentication", "generate_token")
	if err != nil {
		t.Fatal(err)
	}
	if !on {
		t.Fatal("empty config_data means every tool defaults to enabled")
	}
}

func TestToolConfigLoaderEnvironmentOverrides(t *testing.T) {
	const yaml = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      generate_token:
        enabled: false
      validate_token:
        enabled: true
environment_overrides:
  development:
    authentication:
      tools:
        generate_token:
          enabled: true
`
	path := writeFile(t, "tool_config.yaml", yaml)

	// Quirk: _apply_environment_overrides merges the environment block into the top-level
	// config dict, so an "authentication" override lands at the root instead of under
	// "tools" and has no effect on tool enablement.
	dev := config.NewToolConfigLoader(path, envFn(map[string]string{"ENVIRONMENT": "development"}))
	if _, err := dev.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	on, err := dev.IsToolEnabled("authentication", "generate_token")
	if err != nil {
		t.Fatal(err)
	}
	if on {
		t.Fatal("the development override is merged at the wrong level and is a no-op")
	}
	if _, ok := get(t, dev.ConfigData, "authentication").(cmap); !ok {
		t.Fatal("the override should be merged at the top level")
	}

	prod := config.NewToolConfigLoader(path, envFn(map[string]string{"ENVIRONMENT": "production"}))
	if _, err := prod.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	on, err = prod.IsToolEnabled("authentication", "generate_token")
	if err != nil {
		t.Fatal(err)
	}
	if on {
		t.Fatal("no production override, generate_token stays disabled")
	}

	// AUTH_ENABLED=false disables authentication tools regardless of the file.
	off := config.NewToolConfigLoader(path, envFn(map[string]string{"ENVIRONMENT": "development", "AUTH_ENABLED": "false"}))
	if _, err := off.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	on, err = off.IsToolEnabled("authentication", "validate_token")
	if err != nil {
		t.Fatal(err)
	}
	if on {
		t.Fatal("AUTH_ENABLED=false must disable auth tools")
	}
}

func TestToolConfigLoaderValidationErrors(t *testing.T) {
	cases := []struct {
		name    string
		yaml    string
		wantMsg string
	}{
		{"not-dict", "- a\n- b\n", "Failed to load config file: Configuration must be a dictionary"},
		{"bad-version", "version: \"2.0.0\"\ntools: {}\n", "Failed to load config file: Unsupported configuration version: 2.0.0"},
		{"tools-not-dict", "version: \"1.0.0\"\ntools:\n  - x\n", "Failed to load config file: 'tools' section must be a dictionary"},
		{"group-not-dict", "version: \"1.0.0\"\ntools:\n  authentication: 5\n", "Failed to load config file: Tool group 'authentication' must be a dictionary"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			l := config.NewToolConfigLoader(writeFile(t, "c.yaml", tc.yaml), envFn(nil))
			_, err := l.LoadConfig()
			if err == nil || err.Error() != tc.wantMsg {
				t.Fatalf("err = %v, want %q", err, tc.wantMsg)
			}
		})
	}

	l := config.NewToolConfigLoader(writeFile(t, "bad.yaml", "a: [b\n"), envFn(nil))
	_, err := l.LoadConfig()
	if err == nil || len(err.Error()) < len("Invalid YAML in config file:") ||
		err.Error()[:len("Invalid YAML in config file:")] != "Invalid YAML in config file:" {
		t.Fatalf("err = %v, want Invalid YAML prefix", err)
	}
}

func TestToolConfigLoaderEnabledToolsAndDependencies(t *testing.T) {
	const yaml = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      a:
        enabled: true
      b:
        enabled: false
      c: {}
  connection:
    enabled: false
    tools:
      manage_connection:
        enabled: true
global:
  fail_silently_on_missing_deps: true
`
	path := writeFile(t, "c.yaml", yaml)
	l := config.NewToolConfigLoader(path, envFn(map[string]string{"AUTH_ENABLED": "true"}))
	if _, err := l.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	enabled, err := l.GetEnabledTools("authentication")
	if err != nil {
		t.Fatal(err)
	}
	if len(enabled) != 2 || enabled[0] != "a" || enabled[1] != "c" {
		t.Fatalf("enabled = %v, want [a c]", enabled)
	}
	disabledGroup, err := l.GetEnabledTools("connection")
	if err != nil {
		t.Fatal(err)
	}
	if len(disabledGroup) != 0 {
		t.Fatalf("disabled group returned %v", disabledGroup)
	}

	if b, err := l.GetToolConfig("authentication", "a"); err != nil {
		t.Fatal(err)
	} else if get(t, b, "enabled") != true {
		t.Fatalf("tool config a = %v", b)
	}

	avail := &entities.StringSet{}
	ok, err := l.ValidateDependencies("authentication", "a", avail)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Fatal("no dependencies means satisfied")
	}

	// missing dependency, fail_silently default true
	const yaml2 = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      needs_dep:
        enabled: true
        dependencies: ["auth_middleware"]
`
	l2 := config.NewToolConfigLoader(writeFile(t, "c2.yaml", yaml2), envFn(nil))
	if _, err := l2.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	ok, err = l2.ValidateDependencies("authentication", "needs_dep", &entities.StringSet{})
	if err != nil {
		t.Fatal(err)
	}
	if ok {
		t.Fatal("missing dependency should fail")
	}
	if ok, err := l2.ValidateDependencies("authentication", "needs_dep", func() *entities.StringSet {
		s := &entities.StringSet{}
		s.Add("auth_middleware")
		return s
	}()); err != nil || !ok {
		t.Fatalf("available dependency: ok=%v err=%v", ok, err)
	}

	// fail_silently false raises ToolConfigError
	const yaml3 = `version: "1.0.0"
tools:
  authentication:
    enabled: true
    tools:
      needs_dep:
        enabled: true
        dependencies: ["auth_middleware"]
global:
  fail_silently_on_missing_deps: false
`
	l3 := config.NewToolConfigLoader(writeFile(t, "c3.yaml", yaml3), envFn(nil))
	if _, err := l3.LoadConfig(); err != nil {
		t.Fatal(err)
	}
	_, err = l3.ValidateDependencies("authentication", "needs_dep", &entities.StringSet{})
	want := "Tool 'needs_dep' has missing dependencies: ['auth_middleware']"
	if err == nil || err.Error() != want {
		t.Fatalf("err = %v, want %q", err, want)
	}
}
