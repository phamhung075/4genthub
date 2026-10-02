package value_objects

import (
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/connection_management/domain/internal/testutil"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func check(t *testing.T, name string, got any, err error, want any) {
	t.Helper()
	w := want.(map[string]any)
	if msg, bad := w["err"]; bad {
		if err == nil || err.Error() != msg {
			t.Fatalf("%s: err %v want %q", name, err, msg)
		}
		return
	}
	if err != nil {
		t.Fatalf("%s: unexpected %v", name, err)
	}
	if !reflect.DeepEqual(testutil.Norm(got), w["ok"]) {
		t.Fatalf("%s:\n got %v\nwant %v", name, testutil.Norm(got), w["ok"])
	}
}

func strs(v any) []string {
	out := []string{}
	for _, s := range v.([]any) {
		out = append(out, s.(string))
	}
	return out
}

// decode turns the fixture's {"__od__": ...} dicts back into ordered maps, recursively.
func decode(v any) any {
	switch x := v.(type) {
	case map[string]any:
		if pairs, ok := x["__od__"]; ok {
			m := tmentities.NewOrderedMap[any]()
			for _, p := range pairs.([]any) {
				pp := p.([]any)
				m.Set(pp[0].(string), decode(pp[1]))
			}
			return m
		}
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = decode(e)
		}
		return out
	}
	return v
}

func od(v any) *tmentities.OrderedMap[any] { return decode(v).(*tmentities.OrderedMap[any]) }

func plain(v any) map[string]any {
	m := map[string]any{}
	if raw, ok := v.(map[string]any); ok && raw["__od__"] == nil {
		return raw
	}
	for _, p := range v.(map[string]any)["__od__"].([]any) {
		pp := p.([]any)
		m[pp[0].(string)] = pp[1]
	}
	return m
}

func TestValueObjectsMatchPython(t *testing.T) {
	fx := testutil.Load(t, "testdata/value_objects_cases.json").(map[string]any)

	for i, c := range fx["health"].([]any) {
		a := c.([]any)[0].([]any)
		h, err := NewConnectionHealth(a[0].(string), a[1].(string), a[2].(float64), a[3].(float64), plain(a[4]), strs(a[5]), strs(a[6]))
		var d any
		if err == nil {
			d = h.ToDict()
		}
		check(t, "health", d, err, c.([]any)[1])
		_ = i
	}
	for _, c := range fx["status"].([]any) {
		a := c.([]any)[0].([]any)
		s, err := NewServerStatus(a[0].(string), a[1].(string), a[2].(string), a[3].(float64), int(a[4].(float64)), od(a[5]))
		var d any
		if err == nil {
			d = s.ToDict()
		}
		check(t, "status", d, err, c.([]any)[1])
	}
	for _, c := range fx["caps"].([]any) {
		a := c.([]any)[0].([]any)
		actions := tmentities.NewOrderedMap[[]string]()
		for _, p := range a[1].(map[string]any)["__od__"].([]any) {
			pp := p.([]any)
			actions.Set(pp[0].(string), strs(pp[1]))
		}
		caps, err := NewServerCapabilities(strs(a[0]), actions, a[2], a[3], a[4].(string))
		var d any
		if err == nil {
			d = caps.ToDict()
		}
		check(t, "caps", d, err, c.([]any)[1])
	}
	caps, _ := NewServerCapabilities([]string{"a", "b"}, func() *tmentities.OrderedMap[[]string] {
		m := tmentities.NewOrderedMap[[]string]()
		m.Set("x", []string{"1", "2"})
		m.Set("y", []string{})
		return m
	}(), true, false, "v")
	cm := fx["caps_methods"].(map[string]any)
	if float64(caps.GetTotalActionsCount()) != cm["total"] ||
		!reflect.DeepEqual([]any{caps.HasFeature("a"), caps.HasFeature("z")}, cm["f"]) ||
		!reflect.DeepEqual([]any{caps.HasActionCategory("x"), caps.HasActionCategory("q")}, cm["c"]) {
		t.Fatalf("caps methods %v", cm)
	}

	ts := time.Date(2026, 3, 1, 9, 30, 15, 250000000, time.UTC)
	for _, c := range fx["su"].([]any) {
		a := c.([]any)[0].([]any)
		u, err := NewStatusUpdate(a[0].(string), ts, od(a[2]), a[3].(string))
		var d any
		if err == nil {
			d = u.ToDict()
		}
		check(t, "su", d, err, c.([]any)[1])
	}

	Now = func() time.Time { return time.Date(2026, 3, 1, 10, 0, 0, 500000000, time.UTC) }
	details := tmentities.NewOrderedMap[any]()
	details.Set("uptime", 1.0)
	details.Set("health_status", "override")
	facts := fx["fact"].([]any)
	run := []func() (StatusUpdate, error){
		func() (StatusUpdate, error) { return CreateServerHealthUpdate("s", "healthy", details) },
		func() (StatusUpdate, error) { return CreateConnectionUpdate("s", "c1", "established") },
		func() (StatusUpdate, error) { return CreateConnectionUpdate("s", "c1", "lost") },
		func() (StatusUpdate, error) { return CreateConnectionUpdate("s", "c1", "weird") },
		func() (StatusUpdate, error) { return CreateClientRegistrationUpdate("s", true) },
		func() (StatusUpdate, error) { return CreateClientRegistrationUpdate("s", false) },
	}
	for i, f := range run {
		u, err := f()
		var d any
		if err == nil {
			d = u.ToDict()
		}
		check(t, "factory", d, err, facts[i])
	}
}
