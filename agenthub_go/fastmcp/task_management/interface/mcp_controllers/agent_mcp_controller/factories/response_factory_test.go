package factories

// Expectations taken from Python
// task_management/interface/mcp_controllers/agent_mcp_controller/factories/response_factory.py

import (
	"reflect"
	"testing"
)

func TestCreateMissingFieldError(t *testing.T) {
	f := NewAgentResponseFactory(nil)

	got := f.CreateMissingFieldError("name", "register")

	wantKeys := []string{"success", "error", "error_code", "field", "action", "expected", "hint"}
	if !reflect.DeepEqual(got.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
	}
	if v, _ := got.Get("success"); v != false {
		t.Errorf("success = %v, want false", v)
	}
	if v, _ := got.Get("error"); v != "Missing required field: name" {
		t.Errorf("error = %v", v)
	}
	if v, _ := got.Get("error_code"); v != "MISSING_FIELD" {
		t.Errorf("error_code = %v", v)
	}
	if v, _ := got.Get("field"); v != "name" {
		t.Errorf("field = %v", v)
	}
	if v, _ := got.Get("action"); v != "register" {
		t.Errorf("action = %v", v)
	}
	if v, _ := got.Get("expected"); v != "A valid name value" {
		t.Errorf("expected = %v", v)
	}
	if v, _ := got.Get("hint"); v != "Include 'name' in your request for action 'register'" {
		t.Errorf("hint = %v", v)
	}
}

func TestCreateInvalidActionErrorDefaultActions(t *testing.T) {
	f := NewAgentResponseFactory(nil)

	got := f.CreateInvalidActionError("bogus", nil)

	wantKeys := []string{"success", "error", "error_code", "field", "expected", "hint"}
	if !reflect.DeepEqual(got.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
	}
	if v, _ := got.Get("error"); v != "Invalid action" {
		t.Errorf("error = %v", v)
	}
	if v, _ := got.Get("error_code"); v != "INVALID_ACTION" {
		t.Errorf("error_code = %v", v)
	}
	if v, _ := got.Get("expected"); v != "One of: register, assign, get, list, update, unassign, unregister, rebalance" {
		t.Errorf("expected = %v", v)
	}
	if v, _ := got.Get("hint"); v != "Invalid action: bogus. Use one of the supported actions." {
		t.Errorf("hint = %v", v)
	}
}

func TestCreateInvalidActionErrorExplicitActions(t *testing.T) {
	f := NewAgentResponseFactory(nil)

	got := f.CreateInvalidActionError("x", []string{"a", "b"})

	if v, _ := got.Get("expected"); v != "One of: a, b" {
		t.Errorf("expected = %v", v)
	}
}
