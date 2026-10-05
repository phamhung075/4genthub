package utils

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func om(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func TestParameterCoercionTypesAndOrder(t *testing.T) {
	in := om("limit", "5", "include_context", "true", "query", "test")
	got := CoerceParameterTypes(in)
	if got.Len() != 3 {
		t.Fatalf("len=%d", got.Len())
	}
	wantKeys := []string{"limit", "include_context", "query"}
	for i, k := range wantKeys {
		if got.Keys()[i] != k {
			t.Errorf("key %d = %q want %q", i, got.Keys()[i], k)
		}
	}
	if v, _ := got.Get("limit"); v != 5 {
		t.Errorf("limit=%#v want 5", v)
	}
	if v, _ := got.Get("include_context"); v != true {
		t.Errorf("include_context=%#v want true", v)
	}
	if v, _ := got.Get("query"); v != "test" {
		t.Errorf("query=%#v", v)
	}
	// input unchanged
	if v, _ := in.Get("limit"); v != "5" {
		t.Errorf("input mutated: %#v", v)
	}
}

func TestParameterCoercionBoolForms(t *testing.T) {
	got := CoerceParameterTypes(om("force", "NO", "recursive", "Yes", "enabled", "0"))
	if v, _ := got.Get("force"); v != false {
		t.Errorf("force=%#v", v)
	}
	if v, _ := got.Get("recursive"); v != true {
		t.Errorf("recursive=%#v", v)
	}
	if v, _ := got.Get("enabled"); v != false {
		t.Errorf("enabled=%#v", v)
	}
}

func TestParameterCoercionErrors(t *testing.T) {
	_, err := ParameterTypeCoercer{}.CoerceToInt("", "limit")
	if err == nil || err.Msg != "Parameter 'limit' cannot be empty string when expecting integer" {
		t.Fatalf("empty err=%#v", err)
	}
	_, err = ParameterTypeCoercer{}.CoerceToInt("abc", "limit")
	if err == nil || err.Msg != "Parameter 'limit' value 'abc' cannot be converted to integer" {
		t.Fatalf("abc err=%#v", err)
	}
	_, err = ParameterTypeCoercer{}.CoerceToBool("maybe", "force")
	want := "Parameter 'force' value 'maybe' is not a valid boolean string. Valid values: 0, 1, active, disabled, enabled, f, false, inactive, n, no, off, on, t, true, y, yes"
	if err == nil || err.Msg != want {
		t.Fatalf("bool err=%q", err)
	}
}

func TestValidateParametersSuccessShape(t *testing.T) {
	params := om("limit", "5")
	res := ValidateParameters("search", params)
	want := []string{"success", "action", "original_params", "coerced_params", "coercion_applied"}
	for i, k := range want {
		if res.Keys()[i] != k {
			t.Fatalf("key %d = %q", i, res.Keys()[i])
		}
	}
	if v, _ := res.Get("success"); v != true {
		t.Errorf("success=%#v", v)
	}
	if v, _ := res.Get("coercion_applied"); v != true {
		t.Errorf("coercion_applied=%#v", v)
	}
	op, _ := res.Get("original_params")
	if op != params {
		t.Errorf("original_params not identity")
	}
	cp := res.Get
	_ = cp
}

func TestValidateParametersErrorShape(t *testing.T) {
	res := ValidateParameters("search", om("limit", ""))
	want := []string{"success", "error", "error_code", "parameter", "provided_value", "expected_type", "hint"}
	for i, k := range want {
		if res.Keys()[i] != k {
			t.Fatalf("key %d = %q", i, res.Keys()[i])
		}
	}
	if v, _ := res.Get("error_code"); v != "PARAMETER_COERCION_ERROR" {
		t.Errorf("error_code=%#v", v)
	}
	if v, _ := res.Get("provided_value"); v != "" {
		t.Errorf("provided_value=%#v", v)
	}
	if v, _ := res.Get("expected_type"); v != "integer" {
		t.Errorf("expected_type=%#v", v)
	}
}

func TestMCPParameterValidatorSuccess(t *testing.T) {
	res := ValidateMCPParameters("search", om("limit", "5", "include_context", "true"))
	want := []string{"success", "coerced_params", "action", "validation_notes"}
	for i, k := range want {
		if res.Keys()[i] != k {
			t.Fatalf("key %d = %q", i, res.Keys()[i])
		}
	}
	cp, _ := res.Get("coerced_params")
	m := cp.(*entities.OrderedMap[any])
	if v, _ := m.Get("limit"); v != 5 {
		t.Errorf("limit=%#v", v)
	}
}

func TestCreateFlexibleSchemaSharesPropertiesQuirk(t *testing.T) {
	props := entities.NewOrderedMap[any]()
	props.Set("limit", om("type", "integer"))
	schema := entities.NewOrderedMap[any]()
	schema.Set("properties", props)

	flex := CreateFlexibleSchema(schema)
	origProp, _ := props.Get("limit")
	om, ok := origProp.(*entities.OrderedMap[any])
	if !ok || !om.Has("anyOf") {
		t.Fatalf("Python shallow-copy quirk not reproduced; orig=%#v", origProp)
	}
	flexProps, _ := flex.Get("properties")
	if flexProps != any(props) {
		t.Errorf("properties not shared: %#v", flexProps)
	}
}
