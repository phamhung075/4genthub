package exceptions

import (
	"errors"
	"testing"
)

func TestHierarchyAsIsInstance(t *testing.T) {
	var err error = NewTaskNotFoundError("abc123")
	var base *TaskDomainError
	if !errors.As(err, &base) || base.ErrorCode != "TASK_NOT_FOUND" || base.Recoverable {
		t.Fatal(base)
	}
	var nf *TaskNotFoundError
	if !errors.As(err, &nf) || err.Error() != "Task with ID abc123 not found" {
		t.Fatal(err)
	}
	if e := NewTaskNotFoundError("Task xyz9 not found"); e.TaskID != "xyz9" || e.Error() != "Task xyz9 not found" {
		t.Fatal(e.TaskID)
	}
	var vs *VisionSystemError
	if !errors.As(error(NewMissingCompletionSummaryError("t1")), &vs) {
		t.Fatal("vision hierarchy")
	}
	var ce *ContextEnforcementError
	if !errors.As(error(NewMissingCompletionSummaryError("t1")), &ce) || *ce.TaskID != "t1" {
		t.Fatal("ctx enforcement")
	}
}

func TestTaskManagementDefaults(t *testing.T) {
	e := NewResourceNotFoundException("Task", "42", "")
	d := e.ToDict()
	if d["error_code"] != "TASK_NOT_FOUND" || d["message"] != "Task with id '42' not found" || d["severity"] != "medium" ||
		d["recoverable"] != false || d["type"] != "ResourceNotFoundException" {
		t.Fatal(d)
	}
	v := NewValidationError("bad", "name", 5)
	if v.ErrorCode != "VALIDATION_ERROR" || v.Context["value"] != "5" || v.ToDict()["type"] != "ValidationError" {
		t.Fatal(v.ToDict())
	}
	var base *ValidationException
	if !errors.As(error(v), &base) {
		t.Fatal("ValidationError is-a ValidationException")
	}
}

func TestDatabaseQuirksPreserved(t *testing.T) {
	c := NewDatabaseConnectionException("")
	if c.Msg != "Failed to connect to database" || c.ErrorCode != "DATABASE_ERROR" || string(c.Severity) != "high" {
		t.Fatal(c.ToDict())
	}
	r := NewRepositoryError("x", "repo")
	if r.Context["operation"] != "repository" || r.Context["repository"] != nil || r.ErrorCode != "DATABASE_ERROR" {
		t.Fatal(r.Context)
	}
	if NewExternalServiceException("keycloak", "down", 503).ErrorCode != "KEYCLOAK_SERVICE_ERROR" {
		t.Fatal("service code")
	}
	if e := NewTaskCompletionError("m", []map[string]any{{"id": 1}}); e.Context["incomplete_count"] != 1 || e.ErrorCode != "SUBTASKS_NOT_COMPLETE" {
		t.Fatal(e.Context)
	}
}

func TestReviewFixes(t *testing.T) {
	if NewUserAuthenticationRequiredError("").Error() != "This operation requires user authentication. No user ID was provided." {
		t.Fatal(NewUserAuthenticationRequiredError("").Error())
	}
	cases := map[string]any{"True": true, "1.0": 1.0, "['a', 1]": []any{"a", 1}, "{'a': 1}": map[string]any{"a": 1}, "None": nil}
	for want, in := range cases {
		e := NewValidationException("m", "f", in)
		got, ok := e.Context["value"]
		if in == nil { // value None is skipped entirely, as in Python
			if ok {
				t.Fatal("nil value should not be recorded")
			}
			continue
		}
		if got != want {
			t.Errorf("%v -> %v want %v", in, got, want)
		}
	}
	ctx := map[string]any{}
	if r := NewRepositoryError("x", "repo", WithContext(ctx)); r.Context["repository"] != "repo" || r.Context["operation"] != "repository" {
		t.Fatal(r.Context)
	}
	if e := NewTaskNotFoundError("Task é1 not found"); e.TaskID != "é1" {
		t.Fatal(e.TaskID)
	}
}
