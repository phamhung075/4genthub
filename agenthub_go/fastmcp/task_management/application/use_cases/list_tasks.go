package use_cases

import (
	"context"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ListTasksTaskRepository is the task repository surface used by ListTasksUseCase:
// find_by_criteria plus the batch completed-subtask counts.
type ListTasksTaskRepository interface {
	FindByCriteria(ctx context.Context, filters map[string]any, query repositories.ListQuery) ([]*entities.Task, error)
	CountByCriteria(ctx context.Context, filters map[string]any) (int, error)
	GetCompletedSubtaskCounts(ctx context.Context, taskIDs []string) (map[string]int, error)
}

// ListTasksUseCase ports list_tasks.ListTasksUseCase.
type ListTasksUseCase struct {
	taskRepository      ListTasksTaskRepository
	gitBranchRepository dtostask.GitBranchBatchRepository // may be nil
	progressEvents      dtostask.TaskProgressEventsByTask // may be nil
}

// NewListTasksUseCase builds the use case; gitBranchRepository may be nil, and progressEvents may be
// nil too - then every row's details is empty, which is what an unwired seam has always meant here.
func NewListTasksUseCase(taskRepository ListTasksTaskRepository,
	gitBranchRepository dtostask.GitBranchBatchRepository,
	progressEvents dtostask.TaskProgressEventsByTask) *ListTasksUseCase {
	return &ListTasksUseCase{
		taskRepository:      taskRepository,
		gitBranchRepository: gitBranchRepository,
		progressEvents:      progressEvents,
	}
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

	tasks, err := uc.taskRepository.FindByCriteria(ctx, filters, repositories.ListQuery{
		Limit:     request.Limit,
		Offset:    request.Offset,
		SortBy:    listQueryString(request.SortBy),
		SortOrder: listQueryString(request.SortOrder),
	})
	if err != nil {
		return nil, err
	}
	total, err := uc.taskRepository.CountByCriteria(ctx, filters)
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
	if request.Offset != nil && *request.Offset != 0 {
		filtersApplied.Set("offset", *request.Offset)
	}
	if request.SortBy != nil && *request.SortBy != "" {
		filtersApplied.Set("sort_by", *request.SortBy)
	}
	if request.SortOrder != nil && *request.SortOrder != "" {
		filtersApplied.Set("sort_order", *request.SortOrder)
	}

	response, err := dtostask.TaskListResponseFromDomainList(ctx, tasks, uc.gitBranchRepository,
		uc.taskRepository, uc.progressEvents, filtersApplied, nil)
	if err != nil {
		return nil, err
	}
	response.Total = total
	return response, nil
}

// listQueryString dereferences an optional ordering field; empty means the repository default.
func listQueryString(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}
