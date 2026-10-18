package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// SearchTasksUseCase ports search_tasks.SearchTasksUseCase.
type SearchTasksUseCase struct {
	taskRepository repositories.TaskRepository
	progressEvents task.TaskProgressEventsByTask // may be nil
}

// NewSearchTasksUseCase builds the use case; progressEvents may be nil, and then every row's details
// is empty.
func NewSearchTasksUseCase(taskRepository repositories.TaskRepository,
	progressEvents task.TaskProgressEventsByTask) *SearchTasksUseCase {
	return &SearchTasksUseCase{taskRepository: taskRepository, progressEvents: progressEvents}
}

// Execute ports execute(). Python calls
// TaskListResponse.from_domain_list(tasks, query=request.query); the git branch and
// task repositories default to None, so those two batch dependencies are nil here. The ledger is the
// exception: a row's details render from it, so search takes the same reader the list takes, or its
// results would be the one surface whose details are empty.
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
	tasks, err := uc.taskRepository.Search(ctx, request.Query, filters, request.Limit, request.Offset)
	if err != nil {
		return nil, err
	}
	query := request.Query
	return task.TaskListResponseFromDomainList(ctx, tasks, nil, nil, uc.progressEvents, nil, &query)
}
