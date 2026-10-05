package use_cases

import (
	"context"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ListTasksTaskRepository is the task repository surface used by ListTasksUseCase:
// find_by_criteria plus the batch completed-subtask counts.
type ListTasksTaskRepository interface {
	FindByCriteria(ctx context.Context, filters map[string]any, limit *int) ([]*entities.Task, error)
	GetCompletedSubtaskCounts(ctx context.Context, taskIDs []string) (map[string]int, error)
}

// ListTasksUseCase ports list_tasks.ListTasksUseCase.
type ListTasksUseCase struct {
	taskRepository      ListTasksTaskRepository
	gitBranchRepository dtostask.GitBranchBatchRepository // may be nil
}

// NewListTasksUseCase builds the use case; gitBranchRepository may be nil.
func NewListTasksUseCase(taskRepository ListTasksTaskRepository,
	gitBranchRepository dtostask.GitBranchBatchRepository) *ListTasksUseCase {
	return &ListTasksUseCase{taskRepository: taskRepository, gitBranchRepository: gitBranchRepository}
}

// Execute lists tasks with optional filtering.
func (uc *ListTasksUseCase) Execute(ctx context.Context,
	request *dtostask.ListTasksRequest) (*dtostask.TaskListResponse, error) {

	filters := map[string]any{}
	if request.Status != nil && *request.Status != "" {
		status, err := value_objects.NewTaskStatus(*request.Status)
		if err != nil {
			return nil, err
		}
		filters["status"] = status
	}
	if request.Priority != nil && *request.Priority != "" {
		priority, err := value_objects.NewPriority(*request.Priority)
		if err != nil {
			return nil, err
		}
		filters["priority"] = priority
	}
	if len(request.Assignees) > 0 {
		filters["assignees"] = request.Assignees
	}
	if len(request.Labels) > 0 {
		filters["labels"] = request.Labels
	}
	if request.GitBranchID != nil && *request.GitBranchID != "" {
		filters["git_branch_id"] = *request.GitBranchID
	}

	tasks, err := uc.taskRepository.FindByCriteria(ctx, filters, request.Limit)
	if err != nil {
		return nil, err
	}

	filtersApplied := entities.NewOrderedMap[any]()
	if request.Status != nil && *request.Status != "" {
		filtersApplied.Set("status", *request.Status)
	}
	if request.Priority != nil && *request.Priority != "" {
		filtersApplied.Set("priority", *request.Priority)
	}
	if len(request.Assignees) > 0 {
		filtersApplied.Set("assignees", request.Assignees)
	}
	if len(request.Labels) > 0 {
		filtersApplied.Set("labels", request.Labels)
	}
	if request.GitBranchID != nil && *request.GitBranchID != "" {
		filtersApplied.Set("git_branch_id", *request.GitBranchID)
	}
	if request.Limit != nil && *request.Limit != 0 {
		filtersApplied.Set("limit", *request.Limit)
	}

	return dtostask.TaskListResponseFromDomainList(ctx, tasks, uc.gitBranchRepository,
		uc.taskRepository, filtersApplied, nil)
}
