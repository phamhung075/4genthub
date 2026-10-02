package handlers

import (
	"context"
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

func TestAgentHandlerRequiresBranchIdentifier(t *testing.T) {
	stub := &stubFormatter{}
	h := NewGitBranchAgentHandler(stub)

	h.AssignAgent(context.Background(), nil, "proj-1", nil, nil, "agent-1")

	if stub.op != "assign_agent" || stub.code != ErrorCodeValidation {
		t.Fatalf("op/code = %q/%q", stub.op, stub.code)
	}
	if stub.msg != "Either git_branch_id or git_branch_name must be provided" {
		t.Fatalf("message = %q", stub.msg)
	}
	if got := stub.meta.Keys(); len(got) != 2 || got[0] != "project_id" || got[1] != "agent_id" {
		t.Fatalf("metadata keys = %v", got)
	}
}

// The Python facade has no archive_git_branch attribute; the AttributeError is
// caught and returned as this exact error response.
func TestArchiveGitBranchKeepsAttributeErrorQuirk(t *testing.T) {
	stub := &stubFormatter{}
	h := NewGitBranchAdvancedHandler(stub)

	h.ArchiveGitBranch(context.Background(), nil, "proj-1", "branch-1")

	if stub.op != "archive" || stub.code != ErrorCodeOperationFailed {
		t.Fatalf("op/code = %q/%q", stub.op, stub.code)
	}
	want := "Failed to archive git branch: 'GitBranchApplicationFacade' object has no attribute 'archive_git_branch'"
	if stub.msg != want {
		t.Fatalf("message = %q", stub.msg)
	}
}
