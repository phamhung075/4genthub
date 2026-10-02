package factories

// Project Operation Factory (Python operation_factory.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// ProjectCRUDHandler is the consumer-side port of
// project_mcp_controller/handlers/crud_handler.py, which has no Go port yet.
type ProjectCRUDHandler interface {
	CreateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, name string, description, userID *string) *entities.OrderedMap[any]
	GetProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name *string) *entities.OrderedMap[any]
	ListProjects(ctx context.Context, facade *facades.ProjectApplicationFacade) *entities.OrderedMap[any]
	UpdateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name, description *string) *entities.OrderedMap[any]
	DeleteProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force *bool) *entities.OrderedMap[any]
}

// ProjectMaintenanceHandler is the consumer-side port of
// project_mcp_controller/handlers/maintenance_handler.py, which has no Go port yet.
type ProjectMaintenanceHandler interface {
	ProjectHealthCheck(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, userID *string) *entities.OrderedMap[any]
	CleanupObsolete(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any]
	ValidateIntegrity(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any]
	RebalanceAgents(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any]
}

// ProjectOperationParams carries the Python **kwargs consumed by the factory.
type ProjectOperationParams struct {
	ProjectID   *string
	Name        *string
	Description *string
	UserID      *string
	Force       *bool
}

func projectValidOperations() []any {
	return []any{"create", "get", "list", "update", "delete", "project_health_check", "cleanup_obsolete", "validate_integrity", "rebalance_agents"}
}

// ProjectOperationFactory ports ProjectOperationFactory.
type ProjectOperationFactory struct {
	responseFormatter  ResponseFormatter
	crudHandler        ProjectCRUDHandler
	maintenanceHandler ProjectMaintenanceHandler
}

// NewProjectOperationFactory builds the factory. Python constructs the two
// handlers internally from the response formatter; they are injected here
// because their modules are unported.
func NewProjectOperationFactory(responseFormatter ResponseFormatter, crudHandler ProjectCRUDHandler, maintenanceHandler ProjectMaintenanceHandler) *ProjectOperationFactory {
	return &ProjectOperationFactory{
		responseFormatter:  responseFormatter,
		crudHandler:        crudHandler,
		maintenanceHandler: maintenanceHandler,
	}
}

// HandleOperation ports handle_operation(operation, facade, **kwargs).
func (f *ProjectOperationFactory) HandleOperation(ctx context.Context, operation string, facade *facades.ProjectApplicationFacade, p ProjectOperationParams) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Operation failed: %v", r), ErrorCodeOperationFailed, metaMap("operation", operation))
		}
	}()

	switch operation {
	case "create", "get", "list", "update", "delete":
		return f.handleCRUDOperation(ctx, operation, facade, p)
	case "project_health_check", "cleanup_obsolete", "validate_integrity", "rebalance_agents":
		return f.handleMaintenanceOperation(ctx, operation, facade, p)
	default:
		return f.responseFormatter.CreateErrorResponse(
			operation,
			fmt.Sprintf("Unknown operation: %s", operation),
			ErrorCodeInvalidOperation,
			metaMap("valid_operations", projectValidOperations()),
		)
	}
}

func (f *ProjectOperationFactory) handleCRUDOperation(ctx context.Context, operation string, facade *facades.ProjectApplicationFacade, p ProjectOperationParams) *entities.OrderedMap[any] {
	switch operation {
	case "create":
		name := ""
		if p.Name != nil {
			name = *p.Name
		}
		return f.crudHandler.CreateProject(ctx, facade, name, p.Description, p.UserID)
	case "get":
		return f.crudHandler.GetProject(ctx, facade, p.ProjectID, p.Name)
	case "list":
		return f.crudHandler.ListProjects(ctx, facade)
	case "update":
		return f.crudHandler.UpdateProject(ctx, facade, p.ProjectID, p.Name, p.Description)
	case "delete":
		return f.crudHandler.DeleteProject(ctx, facade, p.ProjectID, p.Force)
	default:
		return f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Unsupported CRUD operation: %s", operation), ErrorCodeInvalidOperation, nil)
	}
}

func (f *ProjectOperationFactory) handleMaintenanceOperation(ctx context.Context, operation string, facade *facades.ProjectApplicationFacade, p ProjectOperationParams) *entities.OrderedMap[any] {
	force := false
	if p.Force != nil {
		force = *p.Force
	}

	switch operation {
	case "project_health_check":
		return f.maintenanceHandler.ProjectHealthCheck(ctx, facade, p.ProjectID, p.UserID)
	case "cleanup_obsolete":
		return f.maintenanceHandler.CleanupObsolete(ctx, facade, p.ProjectID, force, p.UserID)
	case "validate_integrity":
		return f.maintenanceHandler.ValidateIntegrity(ctx, facade, p.ProjectID, force, p.UserID)
	case "rebalance_agents":
		return f.maintenanceHandler.RebalanceAgents(ctx, facade, p.ProjectID, force, p.UserID)
	default:
		return f.responseFormatter.CreateErrorResponse(operation, fmt.Sprintf("Unsupported maintenance operation: %s", operation), ErrorCodeInvalidOperation, nil)
	}
}
