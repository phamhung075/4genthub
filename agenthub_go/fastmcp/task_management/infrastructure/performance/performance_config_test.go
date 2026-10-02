package performance_test

import (
	"os"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/performance"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func TestPerformanceConfigParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/perf_cases.json")
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
		cfg, err := performance.LoadConfig(func(k string) (string, bool) { v, ok := env[k]; return v, ok })
		got := entities.NewOrderedMap[any]()
		if err != nil {
			got.Set("exc", "ValueError")
			got.Set("msg", err.Error())
		} else {
			ok := entities.NewOrderedMap[any]()
			ok.Set("config", cfg.GetConfig())
			ok.Set("perf", cfg.IsPerformanceMode())
			got.Set("ok", ok)
		}
		g, _ := tmvo.PyJSONDumps(got, -1)
		w, _ := tmvo.PyJSONDumps(field(c, "out"), -1)
		if g != w {
			t.Fatalf("case %d env %v:\n got  %s\n want %s", i, env, g, w)
		}
	}
}
