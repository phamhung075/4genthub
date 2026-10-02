package factories

// Context Operation Factory
// (Python unified_context_controller/factories/operation_factory.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/unified_context_controller/handlers"
)

// ContextOperationFactory coordinates unified context operations.
type ContextOperationFactory struct {
	responseFormatter handlers.ContextResponseFormatter
	contextHandler    *handlers.ContextOperationHandler
}

// NewContextOperationFactory ports __init__(response_formatter).
func NewContextOperationFactory(responseFormatter handlers.ContextResponseFormatter) *ContextOperationFactory {
	return &ContextOperationFactory{
		responseFormatter: responseFormatter,
		contextHandler:    handlers.NewContextOperationHandler(responseFormatter),
	}
}

// HandleOperation ports handle_operation, mirroring the Python
// `except Exception` fallback (which also catches panics in Go).
func (f *ContextOperationFactory) HandleOperation(ctx context.Context, facade *facades.UnifiedContextFacade, action string, kwargs map[string]any) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			operation := "manage_context." + action
			metadata := entities.NewOrderedMap[any]()
			metadata.Set("operation", operation)
			result = f.responseFormatter.CreateErrorResponse(
				operation,
				"Operation failed: "+fmt.Sprint(r),
				"OPERATION_FAILED",
				metadata,
			)
		}
	}()

	return f.contextHandler.HandleContextOperation(ctx, facade, action, kwargs)
}
