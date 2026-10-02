package utilities

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

type refArgs map[string]string

func toMap(r ValidationResult) map[string]any {
	m := map[string]any{"is_valid": r.IsValid, "id_type": string(r.IDType), "original": r.OriginalValue,
		"normalized": nil, "error": nil, "warnings": nil, "metadata": nil}
	if r.NormalizedValue != nil {
		m["normalized"] = *r.NormalizedValue
	}
	if r.ErrorMessage != nil {
		m["error"] = *r.ErrorMessage
	}
	if r.Warnings != nil {
		m["warnings"] = r.Warnings
	}
	if r.Metadata != nil {
		m["metadata"] = r.Metadata
	}
	b, _ := json.Marshal(m)
	var out map[string]any
	_ = json.Unmarshal(b, &out)
	return out
}

// pick keeps only the comparable keys of a reference case.
func pick(c map[string]any) map[string]any {
	out := map[string]any{}
	for _, k := range []string{"is_valid", "id_type", "original", "normalized", "error", "warnings", "metadata"} {
		out[k] = c[k]
	}
	return out
}

func optStr(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

// Every expectation in testdata/id_validator_cases.json was produced by running the
// Python IDValidator.
func TestIDValidatorAgainstPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/id_validator_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var ref struct {
		Detect       []map[string]any `json:"detect"`
		ParamMapping []map[string]any `json:"param_mapping"`
		TaskContext  []map[string]any `json:"task_context"`
		Suggest      map[string]string
		SuggestDef   string `json:"suggest_default"`
	}
	if err := json.Unmarshal(raw, &ref); err != nil {
		t.Fatal(err)
	}
	for _, c := range ref.Detect {
		v := NewIDValidator(c["strict"].(bool))
		hint, _ := c["hint"].(string)
		got := toMap(v.DetectIDType(c["value"].(string), hint))
		if want := pick(c); !reflect.DeepEqual(got, want) {
			t.Errorf("strict=%v value=%q hint=%q\n got  %v\n want %v", c["strict"], c["value"], hint, got, want)
		}
	}
	v := NewIDValidator(true)
	for _, c := range ref.ParamMapping {
		args := c["args"].(map[string]any)
		get := func(k string) *string { return optStr(args[k]) }
		got := toMap(v.ValidateParameterMapping(get("task_id"), get("git_branch_id"), get("project_id"), get("user_id")))
		got["normalized"] = nil
		want := pick(c)
		want["normalized"] = nil
		if !reflect.DeepEqual(got, want) {
			t.Errorf("args=%v\n got  %v\n want %v", args, got, want)
		}
	}
	for _, c := range ref.TaskContext {
		a := c["args"].([]any)
		branch, _ := a[1].(string)
		got := toMap(v.ValidateTaskContext(a[0].(string), branch))
		if want := pick(c); !reflect.DeepEqual(got, want) {
			t.Errorf("args=%v\n got  %v\n want %v", a, got, want)
		}
	}
	if got := v.SuggestFixForConfusion("abc", "ctx"); !reflect.DeepEqual(got, ref.Suggest) {
		t.Errorf("suggest mismatch:\n got  %q\n want %q", got, ref.Suggest)
	}
	if v.SuggestFixForConfusion("z", "")["issue"] != ref.SuggestDef {
		t.Error("default context")
	}
}

func TestPreventIDConfusion(t *testing.T) {
	u := "123e4567-e89b-42d3-a456-426614174000"
	if err := PreventIDConfusion(&u, nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	err := PreventIDConfusion(nil, nil, nil, nil)
	e, ok := err.(*IDValidationError)
	if !ok || e.Msg != "At least one parameter must be provided" {
		t.Fatalf("%v", err)
	}
}
