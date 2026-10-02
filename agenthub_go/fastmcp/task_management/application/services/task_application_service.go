package services

import (
	"context"
	"errors"

	taskdtos "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpTaskAppCreateTaskUseCase is the task_application_service dependency on the
// unported CreateTaskUseCase (Python: CreateTaskUseCase(repo, git_branch_repo)).
type zpTaskAppCreateTaskUseCase interface {
	Execute(request taskdtos.CreateTaskRequest) (*taskdtos.CreateTaskResponse, error)
}

// zpTaskAppGetTaskUseCase is the unported GetTaskUseCase.
type zpTaskAppGetTaskUseCase interface {
	Execute(ctx context.Context, taskID string, generateRules, forceFullGeneration, includeContext bool) (*taskdtos.TaskResponse, error)
}

// zpTaskAppUpdateTaskUseCase is the unported UpdateTaskUseCase.
type zpTaskAppUpdateTaskUseCase interface {
	Execute(request taskdtos.UpdateTaskRequest) (*taskdtos.UpdateTaskResponse, error)
}

// zpTaskAppListTasksUseCase is the unported ListTasksUseCase.
type zpTaskAppListTasksUseCase interface {
	Execute(ctx context.Context, request taskdtos.ListTasksRequest) (*taskdtos.TaskListResponse, error)
}

// zpTaskAppSearchTasksUseCase is the unported SearchTasksUseCase.
type zpTaskAppSearchTasksUseCase interface {
	Execute(ctx context.Context, request taskdtos.SearchTasksRequest) (*taskdtos.TaskListResponse, error)
}

// zpTaskAppDeleteTaskUseCase is the unported DeleteTaskUseCase.
type zpTaskAppDeleteTaskUseCase interface {
	Execute(ctx context.Context, taskID string) (bool, error)
}

// zpTaskAppCompleteTaskUseCase is the unported CompleteTaskUseCase.
type zpTaskAppCompleteTaskUseCase interface {
	Execute(ctx context.Context, taskID string, completionSummary, testingNotes, nextRecommendations *string) (*entities.OrderedMap[any], error)
}

// zpTaskAppContextService is the hierarchical context facade dependency
// (Python: FacadeService.get_unified_context_facade). Only the three calls made
// by this module are declared.
type zpTaskAppContextService interface {
	CreateContext(level, contextID string, data *entities.OrderedMap[any]) error
	UpdateContext(level, contextID string, data *entities.OrderedMap[any]) error
	DeleteContext(level, contextID string) (bool, error)
}

// zpTaskAppDeps bundles the unported use cases this service is built from.
type zpTaskAppDeps struct {
	CreateTask   zpTaskAppCreateTaskUseCase
	GetTask      zpTaskAppGetTaskUseCase
	UpdateTask   zpTaskAppUpdateTaskUseCase
	ListTasks    zpTaskAppListTasksUseCase
	SearchTasks  zpTaskAppSearchTasksUseCase
	DeleteTask   zpTaskAppDeleteTaskUseCase
	CompleteTask zpTaskAppCompleteTaskUseCase
}

// TaskApplicationService mirrors task_application_service.TaskApplicationService.
type TaskApplicationService struct {
	taskRepository             repositories.TaskRepository
	userID                     *string
	hierarchicalContextService zpTaskAppContextService
	contextService             any
	deps                       zpTaskAppDeps
}

// NewTaskApplicationService mirrors TaskApplicationService.__init__. The Python
// constructor builds the use cases from the repository; because those use cases
// are not ported yet they are supplied through zpTaskAppDeps.
func NewTaskApplicationService(taskRepository repositories.TaskRepository, contextService any, userID *string, hierarchicalContextService zpTaskAppContextService, deps zpTaskAppDeps) *TaskApplicationService {
	return &TaskApplicationService{
		taskRepository:             taskRepository,
		userID:                     userID,
		hierarchicalContextService: hierarchicalContextService,
		contextService:             contextService,
		deps:                       deps,
	}
}

// getUserScopedRepository mirrors _get_user_scoped_repository. Go repositories do
// not expose with_user/user_id/session, so the repository is returned unchanged.
func (s *TaskApplicationService) getUserScopedRepository() repositories.TaskRepository {
	return s.taskRepository
}

// WithUser mirrors TaskApplicationService.with_user.
func (s *TaskApplicationService) WithUser(userID string) *TaskApplicationService {
	return NewTaskApplicationService(s.taskRepository, s.contextService, &userID, s.hierarchicalContextService, s.deps)
}

// CreateTask mirrors TaskApplicationService.create_task.
func (s *TaskApplicationService) CreateTask(ctx context.Context, request taskdtos.CreateTaskRequest) (*taskdtos.CreateTaskResponse, error) {
	response, err := s.deps.CreateTask.Execute(request)
	if err != nil {
		return nil, err
	}
	if response != nil && response.Success && response.Task != nil {
		if err := s.hierarchicalContextService.CreateContext("task", response.Task.ID, zpTaskAppTaskContextData(response.Task)); err != nil {
			return nil, err
		}
	}
	return response, nil
}

// GetTask mirrors TaskApplicationService.get_task.
func (s *TaskApplicationService) GetTask(ctx context.Context, taskID string, generateRules, forceFullGeneration, includeContext bool, userID *string, projectID, gitBranchName string) (*taskdtos.TaskResponse, error) {
	response, err := s.deps.GetTask.Execute(ctx, taskID, generateRules, forceFullGeneration, includeContext)
	if err != nil {
		var notFound *exceptions.TaskNotFoundError
		if errors.As(err, &notFound) {
			return nil, nil
		}
		return nil, err
	}
	return response, nil
}

// UpdateTask mirrors TaskApplicationService.update_task.
func (s *TaskApplicationService) UpdateTask(ctx context.Context, request taskdtos.UpdateTaskRequest) (*taskdtos.UpdateTaskResponse, error) {
	response, err := s.deps.UpdateTask.Execute(request)
	if err != nil {
		return nil, err
	}
	if response != nil && response.Success && response.Task != nil {
		if err := s.hierarchicalContextService.UpdateContext("task", response.Task.ID, zpTaskAppTaskContextData(response.Task)); err != nil {
			return nil, err
		}
	}
	return response, nil
}

// ListTasks mirrors TaskApplicationService.list_tasks.
func (s *TaskApplicationService) ListTasks(ctx context.Context, request taskdtos.ListTasksRequest) (*taskdtos.TaskListResponse, error) {
	return s.deps.ListTasks.Execute(ctx, request)
}

// SearchTasks mirrors TaskApplicationService.search_tasks.
func (s *TaskApplicationService) SearchTasks(ctx context.Context, request taskdtos.SearchTasksRequest) (*taskdtos.TaskListResponse, error) {
	return s.deps.SearchTasks.Execute(ctx, request)
}

// DeleteTask mirrors TaskApplicationService.delete_task.
func (s *TaskApplicationService) DeleteTask(ctx context.Context, taskID, userID, projectID, gitBranchName string) (bool, error) {
	result, err := s.deps.DeleteTask.Execute(ctx, taskID)
	if err != nil {
		return false, err
	}
	if result {
		if _, err := s.hierarchicalContextService.DeleteContext("task", taskID); err != nil {
			return false, err
		}
	}
	return result, nil
}

// CompleteTask mirrors TaskApplicationService.complete_task.
func (s *TaskApplicationService) CompleteTask(ctx context.Context, taskID string, completionSummary, testingNotes, nextRecommendations *string) (*entities.OrderedMap[any], error) {
	return s.deps.CompleteTask.Execute(ctx, taskID, completionSummary, testingNotes, nextRecommendations)
}

// GetAllTasks mirrors TaskApplicationService.get_all_tasks.
func (s *TaskApplicationService) GetAllTasks(ctx context.Context) (*taskdtos.TaskListResponse, error) {
	return s.ListTasks(ctx, taskdtos.ListTasksRequest{})
}

// GetTasksByStatus mirrors TaskApplicationService.get_tasks_by_status.
func (s *TaskApplicationService) GetTasksByStatus(ctx context.Context, status string) (*taskdtos.TaskListResponse, error) {
	return s.ListTasks(ctx, taskdtos.ListTasksRequest{Status: &status})
}

// GetTasksByAssignee mirrors TaskApplicationService.get_tasks_by_assignee.
func (s *TaskApplicationService) GetTasksByAssignee(ctx context.Context, assignee string) (*taskdtos.TaskListResponse, error) {
	return s.ListTasks(ctx, taskdtos.ListTasksRequest{Assignees: []string{assignee}})
}

// zpTaskAppTaskContextData builds the context data dict passed to
// create_context/update_context, preserving Python dict ordering.
func zpTaskAppTaskContextData(task *taskdtos.TaskResponse) *entities.OrderedMap[any] {
	inner := entities.NewOrderedMap[any]()
	inner.Set("title", task.Title)
	inner.Set("description", task.Description)
	inner.Set("status", task.Status)
	inner.Set("priority", task.Priority)
	inner.Set("assignees", task.Assignees)
	inner.Set("labels", task.Labels)
	inner.Set("estimated_effort", task.EstimatedEffort)
	var dueDate any
	if task.DueDate != nil && value_objects.PyTruthy(*task.DueDate) {
		dueDate = *task.DueDate
	}
	inner.Set("due_date", dueDate)
	outer := entities.NewOrderedMap[any]()
	outer.Set("task_data", inner)
	return outer
}
