package task_mcp_controller

import (
	"testing"

	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
)

// The factories package defaults its validator and handler constructors to nil;
// this package's init() must replace every one, or manage_task panics on list/create.
func TestFactoryHooksAreWired(t *testing.T) {
	if factories.NewParameterValidator(nil) == nil {
		t.Error("NewParameterValidator returns nil")
	}
	if factories.NewContextValidator(nil) == nil {
		t.Error("NewContextValidator returns nil")
	}
	if factories.NewBusinessValidator(nil) == nil {
		t.Error("NewBusinessValidator returns nil")
	}
	if factories.NewSearchHandler(nil) == nil {
		t.Error("NewSearchHandler returns nil")
	}
	if factories.NewWorkflowHandler(nil, nil) == nil {
		t.Error("NewWorkflowHandler returns nil")
	}
}
