package application

import (
	"errors"
	"testing"
)

func TestTaskManagementExceptionDefaults(t *testing.T) {
	e := NewTaskManagementException("boom", nil, nil)
	if e.Code != "TaskManagementException" {
		t.Fatalf("code = %q", e.Code)
	}
	if e.Details == nil || e.Details.Len() != 0 {
		t.Fatalf("details = %v", e.Details)
	}
}

func TestTaskNotFoundError(t *testing.T) {
	e := NewTaskNotFoundError(5, nil)
	if e.Message != "Task with ID '5' not found" {
		t.Fatalf("message = %q", e.Message)
	}
	if e.Code != "TASK_NOT_FOUND" {
		t.Fatalf("code = %q", e.Code)
	}
	var base *TaskManagementException
	if !errors.As(e, &base) {
		t.Fatalf("errors.As failed")
	}
}

func TestSubtaskNotFoundError(t *testing.T) {
	withTask := NewSubtaskNotFoundError("s", 3, nil)
	if withTask.Message != "Subtask with ID 's' not found in task '3'" {
		t.Fatalf("message = %q", withTask.Message)
	}
	withoutTask := NewSubtaskNotFoundError("s", nil, nil)
	if withoutTask.Message != "Subtask with ID 's' not found" {
		t.Fatalf("message = %q", withoutTask.Message)
	}
}

func TestOtherExceptions(t *testing.T) {
	if m := NewDuplicateError("task", "abc", nil).Message; m != "Duplicate task with identifier 'abc'" {
		t.Fatalf("duplicate = %q", m)
	}
	if m := NewAuthorizationError("delete", strPtr("task"), nil).Message; m != "Not authorized to delete task" {
		t.Fatalf("auth = %q", m)
	}
	if m := NewAuthorizationError("delete", nil, nil).Message; m != "Not authorized to delete" {
		t.Fatalf("auth = %q", m)
	}
	if m := NewExternalServiceError("svc", "op", "m", nil).Message; m != "External service 'svc' failed during 'op': m" {
		t.Fatalf("external = %q", m)
	}
	v := NewValidationError("bad", nil, nil, nil)
	if v.Code != "VALIDATION_ERROR" || v.Details == nil {
		t.Fatalf("validation = %+v", v)
	}
	r := NewRepositoryProviderError("m", nil)
	if r.Code != "REPOSITORY_PROVIDER_ERROR" {
		t.Fatalf("repo = %q", r.Code)
	}
	b := NewBusinessRuleViolationError("r", "msg", nil)
	if b.Rule != "r" || b.Code != "BUSINESS_RULE_VIOLATION" {
		t.Fatalf("business = %+v", b)
	}
}
