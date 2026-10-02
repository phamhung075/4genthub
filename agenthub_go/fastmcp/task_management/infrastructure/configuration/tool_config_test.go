package configuration_test

import (
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func canon(t *testing.T, v any) string {
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func okOrExc(v any, err error) obj {
	m := entities.NewOrderedMap[any]()
	if err != nil {
		m.Set("exc", "AttributeError")
		m.Set("msg", err.Error())
	} else {
		m.Set("ok", v)
	}
	return m
}

func TestToolConfigParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/tool_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	cases, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	for i, c := range cases.([]any) {
		env := map[string]string{}
		em := field(c, "env").(obj)
		for _, k := range em.Keys() {
			v, _ := em.Get(k)
			env[k] = v.(string)
		}
		if f, ok := field(c, "file").(string); ok {
			path := filepath.Join(dir, "c.json")
			if err := os.WriteFile(path, []byte(f), 0o644); err != nil {
				t.Fatal(err)
			}
			env["MCP_TOOL_CONFIG"] = path
		} else if field(c, "missing") == true {
			env["MCP_TOOL_CONFIG"] = filepath.Join(dir, "missing.json")
		}
		getenv := func(k string) (string, bool) { v, ok := env[k]; return v, ok }
		overrides, _ := field(c, "overrides").(obj)
		cfg, cerr := configuration.NewToolConfigWithEnv(getenv, overrides)
		if cerr != nil {
			if _, isExc := field(c, "out").(obj).Get("exc"); !isExc {
				t.Fatalf("case %d: unexpected error %v", i, cerr)
			}
			continue
		}
		enabled := []any{}
		for _, n := range []string{"manage_task", "custom_tool", "x", "unknown", "manage_project", "y"} {
			v, err := cfg.IsEnabledValue(n)
			enabled = append(enabled, okOrExc(v, err))
		}
		out := entities.NewOrderedMap[any]()
		out.Set("config", cfg.Config)
		out.Set("enabled", enabled)
		out.Set("tools", okOrExc(cfg.GetEnabledTools(), nil))
		out.Set("wf", cfg.IsWorkflowGuidanceEnabled())
		got := entities.NewOrderedMap[any]()
		got.Set("ok", out)
		want := field(c, "out")
		// the Python error class/message of a failed accessor is not compared, only that it failed
		if g, w := canon(t, stripMsg(got)), canon(t, stripMsg(want)); g != w {
			t.Fatalf("case %d (file %v env %v overrides %v):\n got  %s\n want %s", i, field(c, "file"), em, field(c, "overrides"), g, w)
		}
	}
}

func stripMsg(v any) any {
	switch x := v.(type) {
	case obj:
		out := entities.NewOrderedMap[any]()
		for _, k := range x.Keys() {
			if k == "msg" {
				continue
			}
			c, _ := x.Get(k)
			out.Set(k, stripMsg(c))
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, c := range x {
			out[i] = stripMsg(c)
		}
		return out
	}
	return v
}
