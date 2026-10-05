package factories

// Expectations taken from Python
// task_management/interface/mcp_controllers/agent_mcp_controller/factories/operation_factory.py

import (
	"context"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers"
)

type stubFormatter struct {
	lastOp   string
	lastMsg  string
	lastCode handlers.ErrorCode
	lastMeta *entities.OrderedMap[any]
}

func (s *stubFormatter) CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	s.lastOp = operation
	s.lastMeta = metadata
	m := entities.NewOrderedMap[any]()
	m.Set("stub", "success")
	return m
}

func (s *stubFormatter) CreateErrorResponse(operation, errorMessage string, errorCode handlers.ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	s.lastOp = operation
	s.lastMsg = errorMessage
	s.lastCode = errorCode
	s.lastMeta = metadata
	m := entities.NewOrderedMap[any]()
	m.Set("stub", "error")
	return m
}

func TestHandleOperationUnknown(t *testing.T) {
	stub := &stubFormatter{}
	f := NewAgentOperationFactory(stub)

	got := f.HandleOperation(context.Background(), "bogus", nil, OperationParams{ProjectID: "p1"})

	if v, _ := got.Get("stub"); v != "error" {
		t.Fatalf("stub result = %v", v)
	}
	if stub.lastOp != "bogus" {
		t.Errorf("operation = %q, want bogus", stub.lastOp)
	}
	if stub.lastMsg != "Unknown operation: bogus" {
		t.Errorf("error = %q", stub.lastMsg)
	}
	if stub.lastCode != "INVALID_OPERATION" {
		t.Errorf("error_code = %q", stub.lastCode)
	}
	want := []string{"register", "assign", "get", "list", "update", "unassign", "unregister", "rebalance"}
	if !reflect.DeepEqual(stub.lastMeta.GetAny("valid_operations"), want) {
		t.Errorf("valid_operations = %v, want %v", stub.lastMeta.GetAny("valid_operations"), want)
	}
	if !reflect.DeepEqual(stub.lastMeta.Keys(), []string{"valid_operations"}) {
		t.Errorf("metadata keys = %v", stub.lastMeta.Keys())
	}
}
