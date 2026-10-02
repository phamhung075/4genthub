package httpapp

import (
	"context"

	taskdto "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
)

// taskFacadeFactory is the services.FacadeService task factory: it builds the
// handler-facing view of a per-user TaskApplicationFacade.
type taskFacadeFactory struct{ provider taskFacadeProvider }

func (f taskFacadeFactory) CreateTaskFacade(projectID, gitBranchID, userID *string) (any, error) {
	validated, err := domain.ValidateUserID(userID, "Task facade creation")
	if err != nil {
		return nil, err
	}
	facade, err := f.provider.TaskFacade(context.Background(), &validated, projectID, gitBranchID)
	if err != nil {
		return nil, err
	}
	return handlerTaskFacade{facade}, nil
}

// handlerTaskFacade adapts TaskApplicationFacade to handlers.TaskHandlerFacade.
type handlerTaskFacade struct {
	f *facades.TaskApplicationFacade
}

// TaskApplicationFacade exposes the wrapped facade to the MCP task controller.
func (h handlerTaskFacade) TaskApplicationFacade() *facades.TaskApplicationFacade { return h.f }

func (h handlerTaskFacade) CreateTask(ctx context.Context, request *taskdto.CreateTaskRequest) *entities.OrderedMap[any] {
	return h.f.CreateTask(ctx, *request)
}

func (h handlerTaskFacade) GetTask(ctx context.Context, taskID string) *entities.OrderedMap[any] {
	return h.f.GetTask(ctx, taskID, true, true)
}

func (h handlerTaskFacade) UpdateTask(ctx context.Context, request *taskdto.UpdateTaskRequest) *entities.OrderedMap[any] {
	return h.f.UpdateTask(ctx, *request)
}

func (h handlerTaskFacade) DeleteTask(ctx context.Context, taskID, userID string) *entities.OrderedMap[any] {
	return h.f.DeleteTask(ctx, taskID, &userID)
}

func (h handlerTaskFacade) ListTasks(ctx context.Context, request *taskdto.ListTasksRequest, includeDependencies, minimal bool) *entities.OrderedMap[any] {
	return h.f.ListTasks(ctx, *request, includeDependencies, minimal, false)
}

func (h handlerTaskFacade) CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes *string, userID string) *entities.OrderedMap[any] {
	return h.f.CompleteTask(ctx, taskID, &completionSummary, testingNotes, &userID)
}

func (h handlerTaskFacade) CountTasks(ctx context.Context, filters map[string]any) any {
	return h.f.CountTasks(ctx, filters)
}

func (h handlerTaskFacade) ListTasksSummary(ctx context.Context, filters map[string]any, offset, limit int) *entities.OrderedMap[any] {
	return h.f.ListTasksSummary(ctx, filters, offset, limit, true)
}

// The Python facade has no get_task_statistics / get_task_with_relations; the API
// handlers call them and report the resulting AttributeError.
func (h handlerTaskFacade) GetTaskStatistics(ctx context.Context, userID string) any {
	panic("'TaskApplicationFacade' object has no attribute 'get_task_statistics'")
}

func (h handlerTaskFacade) GetTaskWithRelations(ctx context.Context, taskID string) any {
	panic("'TaskApplicationFacade' object has no attribute 'get_task_with_relations'")
}
