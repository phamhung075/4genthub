package validators_test

import (
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/validators"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

func str(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

func ts(t *testing.T, v any) *time.Time {
	s := str(v)
	if s == nil {
		return nil
	}
	tm, err := tmvo.ParseISO(*s)
	if err != nil {
		t.Fatal(err)
	}
	return &tm
}

func tuple(ok bool, msg *string) []any {
	if msg == nil {
		return []any{ok, nil}
	}
	return []any{ok, *msg}
}

func result(err error) any {
	if err == nil {
		return map[string]any{"ok": nil}
	}
	return map[string]any{"exc": "LabelValidationError", "msg": err.Error()}
}

func canon(t *testing.T, v any) string {
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func fixResult(v any) any {
	m := v.(*entities.OrderedMap[any])
	if _, ok := m.Get("exc"); ok {
		msg, _ := m.Get("msg")
		return map[string]any{"exc": "LabelValidationError", "msg": msg}
	}
	return map[string]any{"ok": nil}
}

func TestLabelValidatorParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/label_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	cases, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	for i, cv := range cases.([]any) {
		c := cv.(*entities.OrderedMap[any])
		get := func(k string) any { v, _ := c.Get(k); return v }
		out := get("out").(*entities.OrderedMap[any])
		want := func(k string) any { v, _ := out.Get(k); return v }
		name := get("name").(string)
		color, desc := str(get("color")), str(get("description"))
		created, updated := ts(t, get("created")), ts(t, get("updated"))
		check := func(label string, got, w any) {
			if g, ww := canon(t, got), canon(t, w); g != ww {
				t.Fatalf("case %d %s (name %q color %v):\n got  %s\n want %s", i, label, name, get("color"), g, ww)
			}
		}
		check("name", result(validators.ValidateName(name)), fixResult(want("name")))
		check("color", result(validators.ValidateColor(color)), fixResult(want("color")))
		check("desc", result(validators.ValidateDescription(desc)), fixResult(want("desc")))
		ok, msg := validators.ValidateLabelCreation(name, color, desc, created, updated)
		check("create", tuple(ok, msg), want("create"))
		ok, msg = validators.ValidateLabelUpdate(str(get("update_name")), color, desc)
		check("update", tuple(ok, msg), want("update"))
		check("ts", result(validators.ValidateTimestamp(created, "created_at")), fixResult(want("ts")))
		if created != nil && updated != nil {
			check("cons", result(validators.ValidateTimestampsConsistency(*created, *updated)), fixResult(want("cons")))
		}
	}
}
