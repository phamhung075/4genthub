package fastmcp_test

import (
	"os"
	"testing"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func dump(t *testing.T, v any) string {
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestDualModeConfigParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/dual_mode_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	cases, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	for i, c := range cases.([]any) {
		env := map[string]string{}
		em := field(c, "env").(obj)
		for _, k := range em.Keys() {
			v, _ := em.Get(k)
			env[k] = v.(string)
		}
		exists := map[string]bool{}
		for _, p := range field(c, "exists").([]any) {
			exists[p.(string)] = true
		}
		cfg := fastmcp.NewDualModeConfig(fastmcp.ModeEnv{
			Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
			Exists: func(p string) bool { return exists[p] },
			Cwd:    field(c, "cwd").(string),
		})
		res := []any{}
		for _, q := range [][2]string{{"x/y", "project"}, {"/abs", "rules"}, {"f", "rules"}, {"f", "data"}, {"f", "config"}, {"f", "logs"}, {"f", "bogus"}, {"", "data"}} {
			res = append(res, cfg.ResolvePath(q[0], q[1]))
		}
		got := entities.NewOrderedMap[any]()
		ok := entities.NewOrderedMap[any]()
		ok.Set("mode", cfg.RuntimeMode)
		ok.Set("root", cfg.ProjectRoot)
		ok.Set("env", cfg.GetEnvironmentConfig())
		ok.Set("res", res)
		got.Set("ok", ok)
		if g, w := dump(t, got), dump(t, field(c, "out")); g != w {
			t.Fatalf("case %d (env %v exists %v cwd %v):\n got  %s\n want %s", i, env, field(c, "exists"), field(c, "cwd"), g, w)
		}
	}
}
