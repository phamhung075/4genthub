package handlers

// TaskDependencyHandler mirrors dependency_handler.TaskDependencyHandler.
// Dependency operations are "currently handled by dependency_mcp_controller",
// so the Python handler only stores the facade service.
type TaskDependencyHandler struct {
	facadeService TaskFacadeService
}

// NewTaskDependencyHandler builds the handler.
func NewTaskDependencyHandler(facadeService TaskFacadeService) *TaskDependencyHandler {
	return &TaskDependencyHandler{facadeService: facadeService}
}
