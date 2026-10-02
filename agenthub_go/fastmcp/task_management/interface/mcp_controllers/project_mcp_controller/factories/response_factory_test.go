package factories

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type stubFormatter struct {
	op   string
	msg  string
	code ErrorCode
	meta *entities.OrderedMap[any]
}

func (s *stubFormatter) CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return entities.NewOrderedMap[any]()
}

func (s *stubFormatter) CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	s.op, s.msg, s.code, s.meta = operation, errorMessage, errorCode, metadata
	return entities.NewOrderedMap[any]()
}

func TestCreateMissingFieldError(t *testing.T) {
	stub := &stubFormatter{}
	f := NewProjectResponseFactory(stub)

	f.CreateMissingFieldError("project_id", "create")

	if stub.op != "create" {
		t.Fatalf("operation = %q", stub.op)
	}
	if stub.msg != "Missing required field: project_id. Expected: A valid project_id string" {
		t.Fatalf("message = %q", stub.msg)
	}
	if stub.code != "VALIDATION_ERROR" {
		t.Fatalf("code = %q", stub.code)
	}
	if got := stub.meta.Keys(); strings.Join(got, ",") != "field,hint,action" {
		t.Fatalf("metadata keys = %v", got)
	}
	hint, _ := stub.meta.Get("hint")
	if hint != "Include 'project_id' in your request" {
		t.Fatalf("hint = %v", hint)
	}
}

func TestCreateInvalidActionErrorDefaultList(t *testing.T) {
	stub := &stubFormatter{}
	f := NewProjectResponseFactory(stub)

	f.CreateInvalidActionError("bogus", nil)

	if stub.op != "unknown_action" || stub.msg != "Invalid action" || stub.code != "VALIDATION_ERROR" {
		t.Fatalf("op/msg/code = %q/%q/%q", stub.op, stub.msg, stub.code)
	}
	if got := stub.meta.Keys(); strings.Join(got, ",") != "field,expected,hint" {
		t.Fatalf("metadata keys = %v", got)
	}
	expected, _ := stub.meta.Get("expected")
	want := "One of: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents"
	if expected != want {
		t.Fatalf("expected = %q", expected)
	}
	hint, _ := stub.meta.Get("hint")
	if hint != "Invalid action: bogus. Use one of the supported actions." {
		t.Fatalf("hint = %v", hint)
	}
}
