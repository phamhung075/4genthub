package factories

// Agent Operation Factory (Python operation_factory.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers"
)

// OperationParams replaces Python's **kwargs for handle_operation.
type OperationParams struct {
	ProjectID   string
	AgentID     *string
	Name        *string
	CallAgent   *string
	GitBranchID *string
	UserID      *string
}

// AgentOperationFactory ports AgentOperationFactory.
type AgentOperationFactory struct {
	responseFormatter handlers.ResponseFormatter
	crudHandler       *handlers.AgentCRUDHandler
	assignmentHandler *handlers.AgentAssignmentHandler
	rebalanceHandler  *handlers.AgentRebalanceHandler
}

// NewAgentOperationFactory ports __init__(response_formatter).
func NewAgentOperationFactory(responseFormatter handlers.ResponseFormatter) *AgentOperationFactory {
	return &AgentOperationFactory{
		responseFormatter: responseFormatter,
		crudHandler:       handlers.NewAgentCRUDHandler(responseFormatter),
		assignmentHandler: handlers.NewAgentAssignmentHandler(responseFormatter),
		rebalanceHandler:  handlers.NewAgentRebalanceHandler(responseFormatter),
	}
}

// HandleOperation ports handle_operation(operation, facade, **kwargs).
func (f *AgentOperationFactory) HandleOperation(ctx context.Context, operation string, facade *facades.AgentApplicationFacade, params OperationParams) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(
				operation,
				fmt.Sprintf("Operation failed: %v", r),
				handlers.ErrorCodeOperationFailed,
				opMeta("operation", operation),
			)
		}
	}()

	switch operation {
	case "register", "get", "list", "update", "unregister":
		return f.handleCRUDOperation(ctx, operation, facade, params)
	case "assign", "unassign":
		return f.handleAssignmentOperation(ctx, operation, facade, params)
	case "rebalance":
		return f.handleRebalanceOperation(ctx, operation, facade, params)
	default:
		valid := []string{
			"register", "assign", "get", "list",
			"update", "unassign", "unregister", "rebalance",
		}
		return f.responseFormatter.CreateErrorResponse(
			operation,
			"Unknown operation: "+operation,
			handlers.ErrorCodeInvalidOperation,
			opMeta("valid_operations", valid),
		)
	}
}

func (f *AgentOperationFactory) handleCRUDOperation(ctx context.Context, operation string, facade *facades.AgentApplicationFacade, params OperationParams) *entities.OrderedMap[any] {
	projectID := params.ProjectID
	agentID := params.AgentID

	switch operation {
	case "register":
		name := ""
		if params.Name != nil {
			name = *params.Name
		}
		return f.crudHandler.RegisterAgent(ctx, facade, projectID, agentID, name, params.CallAgent, params.UserID)
	case "get":
		return f.crudHandler.GetAgent(ctx, facade, projectID, derefOr(params.AgentID))
	case "list":
		return f.crudHandler.ListAgents(ctx, facade, projectID)
	case "update":
		return f.crudHandler.UpdateAgent(ctx, facade, projectID, derefOr(params.AgentID), params.Name, params.CallAgent, params.UserID)
	case "unregister":
		return f.crudHandler.UnregisterAgent(ctx, facade, projectID, derefOr(params.AgentID), params.UserID)
	default:
		return f.responseFormatter.CreateErrorResponse(
			operation,
			"Unsupported CRUD operation: "+operation,
			handlers.ErrorCodeInvalidOperation,
			entities.NewOrderedMap[any](),
		)
	}
}

func (f *AgentOperationFactory) handleAssignmentOperation(ctx context.Context, operation string, facade *facades.AgentApplicationFacade, params OperationParams) *entities.OrderedMap[any] {
	projectID := params.ProjectID
	agentID := derefOr(params.AgentID)
	gitBranchID := derefOr(params.GitBranchID)

	switch operation {
	case "assign":
		return f.assignmentHandler.AssignAgent(ctx, facade, projectID, agentID, gitBranchID)
	case "unassign":
		return f.assignmentHandler.UnassignAgent(ctx, facade, projectID, agentID, gitBranchID)
	default:
		return f.responseFormatter.CreateErrorResponse(
			operation,
			"Unsupported assignment operation: "+operation,
			handlers.ErrorCodeInvalidOperation,
			entities.NewOrderedMap[any](),
		)
	}
}

func (f *AgentOperationFactory) handleRebalanceOperation(ctx context.Context, operation string, facade *facades.AgentApplicationFacade, params OperationParams) *entities.OrderedMap[any] {
	if operation == "rebalance" {
		return f.rebalanceHandler.RebalanceAgents(ctx, facade, params.ProjectID)
	}
	return f.responseFormatter.CreateErrorResponse(
		operation,
		"Unsupported rebalance operation: "+operation,
		handlers.ErrorCodeInvalidOperation,
		entities.NewOrderedMap[any](),
	)
}

// opMeta builds a one-key metadata OrderedMap.
func opMeta(key string, value any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set(key, value)
	return m
}

// derefOr returns the pointed-to string, or "" for nil (Python None passed to a
// string-typed handler parameter would raise; the controller validates required
// fields before routing, so this only occurs for genuinely optional fields).
func derefOr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
