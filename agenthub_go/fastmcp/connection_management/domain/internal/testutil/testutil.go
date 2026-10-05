// Package testutil holds the helpers shared by the connection_management parity tests.
package testutil

import (
	"encoding/json"
	"os"
	"sort"
	"testing"
	"time"

	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Load reads a Python-generated fixture.
func Load(t *testing.T, path string) any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var v any
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatal(err)
	}
	return v
}

// Norm converts a Go value to the fixture encoding: ordered dicts become
// {"__od__": [[k, v], ...]}, datetimes {"__dt__": iso}, numbers float64.
func Norm(v any) any {
	switch x := v.(type) {
	case nil:
		return nil
	case *tmentities.OrderedMap[any]:
		pairs := []any{}
		for _, k := range x.Keys() {
			e, _ := x.Get(k)
			pairs = append(pairs, []any{k, Norm(e)})
		}
		return map[string]any{"__od__": pairs}
	case *tmentities.OrderedMap[[]string]:
		pairs := []any{}
		for _, k := range x.Keys() {
			e, _ := x.Get(k)
			pairs = append(pairs, []any{k, Norm(e)})
		}
		return map[string]any{"__od__": pairs}
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		pairs := []any{}
		for _, k := range keys {
			pairs = append(pairs, []any{k, Norm(x[k])})
		}
		return map[string]any{"__od__": pairs}
	case time.Time:
		return map[string]any{"__dt__": tmvo.IsoFormatNaive(x)}
	case []string:
		out := []any{}
		for _, s := range x {
			out = append(out, s)
		}
		return out
	case []any:
		out := []any{}
		for _, e := range x {
			out = append(out, Norm(e))
		}
		return out
	case int:
		return float64(x)
	case int64:
		return float64(x)
	}
	return v
}
