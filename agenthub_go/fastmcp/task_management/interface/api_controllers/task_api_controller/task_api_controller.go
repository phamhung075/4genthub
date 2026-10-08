// Package taskapicontroller ports task_management/interface/api_controllers/
// task_api_controller/task_api_controller.TaskAPIController.
package taskapicontroller

import (
	"context"

	taskdto "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/api_controllers/task_api_controller/handlers"
	"agenthub/fastmcp/types"
)

// TaskAPIController mirrors TaskAPIController.
type TaskAPIController struct {
	facadeService     handlers.TaskFacadeService
	crudHandler       *handlers.TaskCrudHandler
	searchHandler     *handlers.TaskSearchHandler
	workflowHandler   *handlers.TaskWorkflowHandler
	dependencyHandler *handlers.TaskDependencyHandler
}

// NewTaskAPIController builds the controller and its handlers. Python resolves
// FacadeService.get_instance() and leaves default_facade nil; the Go service is
// injected.
func NewTaskAPIController(facadeService handlers.TaskFacadeService) *TaskAPIController {
	return &TaskAPIController{
		facadeService:     facadeService,
		crudHandler:       handlers.NewTaskCrudHandler(facadeService),
		searchHandler:     handlers.NewTaskSearchHandler(facadeService),
		workflowHandler:   handlers.NewTaskWorkflowHandler(facadeService),
		dependencyHandler: handlers.NewTaskDependencyHandler(facadeService),
	}
}

// CreateTask mirrors create_task(request, user_id, session).
func (c *TaskAPIController) CreateTask(ctx context.Context, request *taskdto.CreateTaskRequest, userID string) *types.TaskResponse {
	return c.crudHandler.CreateTask(ctx, request, userID)
}

// GetTask mirrors get_task(task_id, user_id, session).
func (c *TaskAPIController) GetTask(ctx context.Context, taskID, userID string) *types.TaskResponse {
	return c.crudHandler.GetTask(ctx, taskID, userID)
}

// UpdateTask mirrors update_task(task_id, request, user_id, session).
func (c *TaskAPIController) UpdateTask(ctx context.Context, taskID string, request *taskdto.UpdateTaskRequest, userID string) *types.TaskResponse {
	return c.crudHandler.UpdateTask(ctx, taskID, request, userID)
}

// DeleteTask mirrors delete_task(task_id, user_id, session).
func (c *TaskAPIController) DeleteTask(ctx context.Context, taskID, userID string) *types.DeleteResponse {
	return c.crudHandler.DeleteTask(ctx, taskID, userID)
}

// ListTasks mirrors list_tasks(request, user_id, session).
func (c *TaskAPIController) ListTasks(ctx context.Context, request *taskdto.ListTasksRequest, userID string) *types.TasksResponse {
	return c.crudHandler.ListTasks(ctx, request, userID)
}

// CompleteTask mirrors complete_task(task_id, completion_summary, testing_notes, user_id, session).
func (c *TaskAPIController) CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes *string, userID string) *types.TaskResponse {
	return c.workflowHandler.CompleteTask(ctx, taskID, completionSummary, testingNotes, userID)
}

// CountTasks mirrors count_tasks(filters, user_id, session).
func (c *TaskAPIController) CountTasks(ctx context.Context, filters *entities.OrderedMap[any], userID string) *types.CountResponse {
	return c.searchHandler.CountTasks(ctx, filters, userID)
}

// ListTasksSummary mirrors list_tasks_summary(filters, offset, limit, user_id, session).
func (c *TaskAPIController) ListTasksSummary(ctx context.Context, filters *entities.OrderedMap[any], offset, limit int, userID string) *types.TaskSummariesResponse {
	return c.searchHandler.ListTasksSummary(ctx, filters, offset, limit, userID)
}
