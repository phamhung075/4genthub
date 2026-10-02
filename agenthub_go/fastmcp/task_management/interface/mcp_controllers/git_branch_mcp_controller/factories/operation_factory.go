package factories

// Git Branch Operation Factory (Python operation_factory.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers"
)

// OperationParams carries the Python **kwargs consumed by the factory.
type OperationParams struct {
	ProjectID            *string
	GitBranchID          *string
	GitBranchName        *string
	GitBranchDescription *string
	AgentID              *string
}

func pyStr(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}

// GitBranchOperationFactory ports GitBranchOperationFactory.
type GitBranchOperationFactory struct {
	responseFormatter handlers.ResponseFormatter
	crudHandler       *handlers.GitBranchCRUDHandler
	agentHandler      *handlers.GitBranchAgentHandler
	advancedHandler   *handlers.GitBranchAdvancedHandler
}

// NewGitBranchOperationFactory ports __init__(response_formatter).
func NewGitBranchOperationFactory(responseFormatter handlers.ResponseFormatter) *GitBranchOperationFactory {
	return &GitBranchOperationFactory{
		responseFormatter: responseFormatter,
		crudHandler:       handlers.NewGitBranchCRUDHandler(responseFormatter),
		agentHandler:      handlers.NewGitBranchAgentHandler(responseFormatter),
		advancedHandler:   handlers.NewGitBranchAdvancedHandler(responseFormatter),
	}
}

// validOperations mirrors the Python list used in the unknown-operation response.
func validOperations() []any {
	return []any{"create", "update", "get", "delete", "list", "assign_agent", "unassign_agent", "get_statistics", "archive", "restore"}
}

// HandleOperation ports handle_operation(operation, facade, **kwargs).
func (f *GitBranchOperationFactory) HandleOperation(ctx context.Context, operation string, facade *facades.GitBranchApplicationFacade, p OperationParams) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Operation failed: %v", r), handlers.ErrorCodeOperationFailed, handlers.MetaMap("operation", operation))
		}
	}()

	switch operation {
	case "create", "update", "get", "delete", "list":
		return f.handleCRUDOperation(ctx, operation, facade, p)
	case "assign_agent", "unassign_agent":
		return f.handleAgentOperation(ctx, operation, facade, p)
	case "get_statistics", "archive", "restore":
		return f.handleAdvancedOperation(ctx, operation, facade, p)
	default:
		return f.responseFormatter.CreateErrorResponse(
			operation,
			fmt.Sprintf("Unknown operation: %s", operation),
			handlers.ErrorCodeInvalidOperation,
			handlers.MetaMap("valid_operations", validOperations()),
		)
	}
}

func (f *GitBranchOperationFactory) handleCRUDOperation(ctx context.Context, operation string, facade *facades.GitBranchApplicationFacade, p OperationParams) *entities.OrderedMap[any] {
	switch operation {
	case "create":
		return f.crudHandler.CreateGitBranch(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchName), p.GitBranchDescription)
	case "update":
		return f.crudHandler.UpdateGitBranch(ctx, facade, pyStr(p.GitBranchID), pyStr(p.ProjectID), p.GitBranchName, p.GitBranchDescription)
	case "get":
		return f.crudHandler.GetGitBranch(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchID))
	case "delete":
		return f.crudHandler.DeleteGitBranch(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchID))
	case "list":
		return f.crudHandler.ListGitBranches(ctx, facade, pyStr(p.ProjectID))
	default:
		return f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Unsupported CRUD operation: %s", operation), handlers.ErrorCodeInvalidOperation, nil)
	}
}

func (f *GitBranchOperationFactory) handleAgentOperation(ctx context.Context, operation string, facade *facades.GitBranchApplicationFacade, p OperationParams) *entities.OrderedMap[any] {
	switch operation {
	case "assign_agent":
		return f.agentHandler.AssignAgent(ctx, facade, pyStr(p.ProjectID), p.GitBranchID, p.GitBranchName, pyStr(p.AgentID))
	case "unassign_agent":
		return f.agentHandler.UnassignAgent(ctx, facade, pyStr(p.ProjectID), p.GitBranchID, p.GitBranchName, pyStr(p.AgentID))
	default:
		return f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Unsupported agent operation: %s", operation), handlers.ErrorCodeInvalidOperation, nil)
	}
}

func (f *GitBranchOperationFactory) handleAdvancedOperation(ctx context.Context, operation string, facade *facades.GitBranchApplicationFacade, p OperationParams) *entities.OrderedMap[any] {
	switch operation {
	case "get_statistics":
		return f.advancedHandler.GetStatistics(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchID))
	case "archive":
		return f.advancedHandler.ArchiveGitBranch(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchID))
	case "restore":
		return f.advancedHandler.RestoreGitBranch(ctx, facade, pyStr(p.ProjectID), pyStr(p.GitBranchID))
	default:
		return f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Unsupported advanced operation: %s", operation), handlers.ErrorCodeInvalidOperation, nil)
	}
}
