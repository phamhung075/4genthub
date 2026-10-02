// Package factories ports
// task_management/interface/mcp_controllers/dependency_mcp_controller/factories.
package factories

import (
	dependency_mcp_controller "agenthub/fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/handlers"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/services"
)

// DependencyControllerFactory creates dependency controller components.
type DependencyControllerFactory struct{}

// CreateController mirrors create_controller.
func (DependencyControllerFactory) CreateController(taskFacade handlers.DependencyTaskFacade) *dependency_mcp_controller.DependencyMCPController {
	return dependency_mcp_controller.NewDependencyMCPController(taskFacade)
}

// CreateHandler mirrors create_handler.
func (DependencyControllerFactory) CreateHandler(taskFacade handlers.DependencyTaskFacade) *handlers.DependencyOperationHandler {
	return handlers.NewDependencyOperationHandler(taskFacade)
}

// CreateDescriptionService mirrors create_description_service.
func (DependencyControllerFactory) CreateDescriptionService() *services.DescriptionService {
	return services.NewDescriptionService()
}
