package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// SearchTasksUseCase ports search_tasks.SearchTasksUseCase.
type SearchTasksUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewSearchTasksUseCase builds the use case.
func NewSearchTasksUseCase(taskRepository repositories.TaskRepository) *SearchTasksUseCase {
	return &SearchTasksUseCase{taskRepository: taskRepository}
}

// Execute ports execute(). Python calls
// TaskListResponse.from_domain_list(tasks, query=request.query); the git branch and
// task repositories default to None, so both batch dependencies are nil here.
func (uc *SearchTasksUseCase) Execute(ctx context.Context, request *task.SearchTasksRequest) (*task.TaskListResponse, error) {
	filters := map[string]any{}
	if request.Status != nil && *request.Status != "" {
		filters["status"] = *request.Status
	}
	if request.Priority != nil && *request.Priority != "" {
		filters["priority"] = *request.Priority
	}
	if len(request.Assignees) > 0 {
		filters["assignees"] = request.Assignees
	}
	if len(request.Labels) > 0 {
		filters["labels"] = request.Labels
	}
	tasks, err := uc.taskRepository.Search(ctx, request.Query, filters, request.Limit)
	if err != nil {
		return nil, err
	}
	query := request.Query
	return task.TaskListResponseFromDomainList(ctx, tasks, nil, nil, nil, &query)
}
