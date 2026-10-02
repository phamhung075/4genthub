package dependency_mcp_controller

import (
	"context"
	"encoding/json"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/handlers"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/services"
)

// DependencyMCPController handles MCP protocol concerns for dependency operations.
type DependencyMCPController struct {
	handler            *handlers.DependencyOperationHandler
	descriptionService *services.DescriptionService
}

// NewDependencyMCPController mirrors DependencyMCPController(task_facade).
func NewDependencyMCPController(taskFacade handlers.DependencyTaskFacade) *DependencyMCPController {
	return &DependencyMCPController{
		handler:            handlers.NewDependencyOperationHandler(taskFacade),
		descriptionService: services.NewDescriptionService(),
	}
}

// HandleDependencyOperations mirrors handle_dependency_operations. Python calls
// coerce_parameter_types, which is the identity for every key used here, so no
// coercion step is ported. register_tools (FastMCP/pydantic) has no Go port.
func (c *DependencyMCPController) HandleDependencyOperations(ctx context.Context, action string, taskID *string, projectID *string, gitBranchName *string, userID *string, dependencyData *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = dependencyControllerInternalError(value_objects.PyStr(r))
		}
	}()

	if projectID == nil || *projectID == "" {
		return dependencyControllerInternalError("project_id is required but was not provided")
	}

	resolvedGitBranchName := "main"
	if gitBranchName != nil && *gitBranchName != "" {
		resolvedGitBranchName = *gitBranchName
	}

	var dependencyDataMap map[string]any
	if dependencyData != nil && value_objects.PyStrip(*dependencyData) != "" {
		var parsed any
		if err := json.Unmarshal([]byte(*dependencyData), &parsed); err != nil {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", false)
			resp.Set("error", "Invalid JSON in dependency_data parameter: "+err.Error())
			resp.Set("error_code", "INVALID_JSON")
			resp.Set("field", "dependency_data")
			resp.Set("hint", "Ensure dependency_data parameter contains valid JSON")
			return resp
		}
		switch value := parsed.(type) {
		case map[string]any:
			dependencyDataMap = value
		case []any:
			// `"dependency_id" not in [...]` is True, so the handler reports MISSING_FIELD.
			dependencyDataMap = nil
		default:
			return dependencyControllerInternalError("argument of type '" + value_objects.PyStr(parsed) + "' is not iterable")
		}
	}

	var taskIDValue string
	if taskID != nil {
		taskIDValue = *taskID
	}
	return c.handler.HandleOperation(ctx, action, taskIDValue, projectID, resolvedGitBranchName, userID, dependencyDataMap)
}

func dependencyControllerInternalError(message string) *entities.OrderedMap[any] {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Dependency operation failed: "+message)
	resp.Set("error_code", "INTERNAL_ERROR")
	resp.Set("details", message)
	return resp
}
