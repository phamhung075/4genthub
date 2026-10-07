package validators

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// fakeFormatter records the error call and returns an ordered map shaped like
// the interface StandardResponseFormatter.create_error_response.
type fakeFormatter struct {
	operation string
	errMsg    string
	errCode   string
	metadata  *entities.OrderedMap[any]
}

func (f *fakeFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.operation, f.errMsg, f.errCode, f.metadata = operation, errorMessage, errorCode, metadata
	d := entities.NewOrderedMap[any]()
	d.Set("status", "error")
	d.Set("error_code", errorCode)
	d.Set("message", errorMessage)
	d.Set("operation", operation)
	d.Set("metadata", metadata)
	d.Set("success", false)
	return d
}

func TestBusinessValidatorCreationTitle(t *testing.T) {
	f := &fakeFormatter{}
	v := NewBusinessValidator(f)
	ok, resp := v.ValidateTaskCreationRules("ab", "branch", nil, nil, nil)
	if ok || resp == nil {
		t.Fatalf("expected failure for short title, got ok=%v resp=%v", ok, resp)
	}
	if f.errCode != errorCodeBusinessRuleViolation {
		t.Fatalf("expected BUSINESS_RULE_VIOLATION, got %q", f.errCode)
	}
	wantMsg := "Business rule violation (title_length): Task title must be at least 3 characters long"
	if f.errMsg != wantMsg {
		t.Fatalf("message mismatch:\n got %q\nwant %q", f.errMsg, wantMsg)
	}
	if rule, _ := f.metadata.Get("rule"); rule != "title_length" {
		t.Fatalf("metadata rule mismatch: %v", rule)
	}
	if hint, _ := f.metadata.Get("hint"); hint != "Provide a more descriptive title for the task" {
		t.Fatalf("metadata hint mismatch: %v", hint)
	}
}

func TestBusinessValidatorCreationDueDatePast(t *testing.T) {
	f := &fakeFormatter{}
	v := NewBusinessValidator(f)
	past := "2020-01-01T00:00:00"
	ok, _ := v.ValidateTaskCreationRules("A good title", "branch", nil, &past, nil)
	if ok {
		t.Fatal("expected past due date to fail")
	}
	if rule, _ := f.metadata.Get("rule"); rule != "due_date_past" {
		t.Fatalf("expected due_date_past, got %v", rule)
	}
}

func TestBusinessValidatorUpdateSelfDependencyAndTransition(t *testing.T) {
	f := &fakeFormatter{}
	v := NewBusinessValidator(f)
	ok, _ := v.ValidateTaskUpdateRules("task-1", nil, nil, nil, nil, []string{"task-1"}, nil)
	if ok {
		t.Fatal("expected self dependency to fail")
	}
	if rule, _ := f.metadata.Get("rule"); rule != "self_dependency" {
		t.Fatalf("expected self_dependency, got %v", rule)
	}

	current := entities.NewOrderedMap[any]()
	current.Set("status", "pending")
	status := "completed"
	ok, _ = v.ValidateTaskUpdateRules("task-1", current, &status, nil, nil, nil, nil)
	if ok {
		t.Fatal("expected invalid status transition pending->completed")
	}
	if rule, _ := f.metadata.Get("rule"); rule != "invalid_status_transition" {
		t.Fatalf("expected invalid_status_transition, got %v", rule)
	}
	if hint, _ := f.metadata.Get("hint"); hint != "Valid transitions from 'pending': ['in_progress', 'blocked', 'cancelled']" {
		t.Fatalf("transition hint mismatch: %v", hint)
	}
}

func TestBusinessValidatorCompletionRequirements(t *testing.T) {
	f := &fakeFormatter{}
	v := NewBusinessValidator(f)
	taskData := entities.NewOrderedMap[any]()
	taskData.Set("priority", "high")
	taskData.Set("title", "Ship")
	short := "too short"
	ok, _ := v.ValidateCompletionRequirements(taskData, &short, nil)
	if ok {
		t.Fatal("expected high priority short summary to fail")
	}
	if rule, _ := f.metadata.Get("rule"); rule != "completion_summary_required" {
		t.Fatalf("expected completion_summary_required, got %v", rule)
	}

	long := "this is a sufficiently long summary"
	ok, _ = v.ValidateCompletionRequirements(taskData, &long, nil)
	if !ok {
		t.Fatal("expected long summary to pass")
	}
}

func TestContextValidatorReservedFieldAndSelfInheritance(t *testing.T) {
	f := &fakeFormatter{}
	v := NewContextValidator(f)
	data := entities.NewOrderedMap[any]()
	data.Set("id", "x")
	ok, resp := v.ValidateContextData(data)
	if ok || resp == nil {
		t.Fatal("expected reserved field to fail")
	}
	if code, _ := resp.Get("error_code"); code != "VALIDATION_ERROR" {
		t.Fatalf("expected VALIDATION_ERROR, got %v", code)
	}
	if op, _ := resp.Get("operation"); op != "validate_context" {
		t.Fatalf("expected operation validate_context, got %v", op)
	}

	parent, child := "ctx", "ctx"
	ok, _ = v.ValidateContextInheritance(&parent, &child)
	if ok {
		t.Fatal("expected self inheritance to fail")
	}
	ok, _ = v.ValidateContextData(nil)
	if !ok {
		t.Fatal("nil context data should pass")
	}
}

func TestParameterValidatorUUIDStatusPriorityDate(t *testing.T) {
	f := &fakeFormatter{}
	v := NewParameterValidator(f)

	valid := "123e4567-e89b-12d3-a456-426614174000"
	badBranch := "not-a-uuid"
	title := "A title"
	ok, _ := v.ValidateCreateTaskParams(&title, &badBranch, nil, nil, nil, nil, nil, nil, nil)
	if ok {
		t.Fatal("expected bad uuid to fail")
	}
	if field, _ := f.metadata.Get("field"); field != "git_branch_id" {
		t.Fatalf("expected git_branch_id field, got %v", field)
	}

	ok, _ = v.ValidateCreateTaskParams(&title, &valid, nil, nil, nil, nil, nil, nil, nil)
	if !ok {
		t.Fatal("expected valid create params to pass")
	}

	status := "bogus"
	ok, _ = v.ValidateCreateTaskParams(&title, &valid, nil, &status, nil, nil, nil, nil, nil)
	if ok {
		t.Fatal("expected bogus status to fail")
	}

	priority := "urgent"
	ok, _ = v.ValidateCreateTaskParams(&title, &valid, nil, nil, &priority, nil, nil, nil, nil)
	if !ok {
		t.Fatal("urgent is a valid priority")
	}

	limit := 2000
	ok, _ = v.ValidateSearchParams(nil, map[string]any{"limit": limit})
	if ok {
		t.Fatal("expected limit > 1000 to fail")
	}
}

// The forms a caller's integers actually arrive in. encoding/json decodes EVERY number as
// float64, and a tool caller may send the digits as a string, so asserting int refused every
// value that came over the wire - while the one case the suite covered, an int literal written
// in Go, is the single form that cannot arrive from JSON. These are the values the reports used.
func TestParameterValidatorSearchIntegersArriveAsJSONNumbers(t *testing.T) {
	f := &fakeFormatter{}
	v := NewParameterValidator(f)

	cases := []struct {
		name  string
		key   string
		value any
		ok    bool
	}{
		{"limit as a decoded JSON number", "limit", float64(3), true},
		{"limit zero", "limit", float64(0), true},
		{"limit as a numeric string", "limit", "3", true},
		{"limit as a Go int (the only form the suite covered)", "limit", 3, true},
		{"limit over the bound", "limit", float64(2000), false},
		{"limit under the bound", "limit", float64(-1), false},
		{"limit that is not a number", "limit", "three", false},
		{"offset as a decoded JSON number", "offset", float64(20), true},
		{"offset zero", "offset", float64(0), true},
		{"offset negative", "offset", float64(-1), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			ok, _ := v.ValidateSearchParams(nil, map[string]any{tc.key: tc.value})
			if ok != tc.ok {
				t.Fatalf("%s = %#v: ok = %v, want %v (last error %q)", tc.key, tc.value, ok, tc.ok, f.errMsg)
			}
		})
	}
}

func TestParameterValidatorProgressCoercion(t *testing.T) {
	f := &fakeFormatter{}
	v := NewParameterValidator(f)
	valid := "123e4567-e89b-12d3-a456-426614174000"
	kwargs := map[string]any{"progress_percentage": "150"}
	ok, _ := v.ValidateUpdateTaskParams(&valid, kwargs)
	if ok {
		t.Fatal("expected 150 to fail")
	}
	kwargs = map[string]any{"progress_percentage": "50"}
	ok, _ = v.ValidateUpdateTaskParams(&valid, kwargs)
	if !ok {
		t.Fatal("expected coerced 50 to pass")
	}
	if kwargs["progress_percentage"] != 50 {
		t.Fatalf("expected normalized int 50, got %v (%T)", kwargs["progress_percentage"], kwargs["progress_percentage"])
	}
}
