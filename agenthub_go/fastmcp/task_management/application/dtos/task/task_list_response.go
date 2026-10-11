package task

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GitBranchBatchRepository is task_list_response.from_domain_list's batch
// dependency (Python calls git_branch_repository.find_by_ids). The domain
// repositories.GitBranchRepository interface does not declare it, so this
// consumer-side interface is declared here; it matches ORMGitBranchRepository,
// whose FindByIDs swallows its own errors like the Python.
type GitBranchBatchRepository interface {
	FindByIDs(ctx context.Context, branchIDs []string) *entities.OrderedMap[*entities.GitBranch]
}

// CompletedSubtaskCounter is task_list_response.from_domain_list's batch
// dependency (Python calls task_repository.get_completed_subtask_counts).
type CompletedSubtaskCounter interface {
	GetCompletedSubtaskCounts(ctx context.Context, taskIDs []string) (map[string]int, error)
}

// TaskProgressEventsByTask is the ledger as a LIST needs it: every listed task's progress entries in
// one read, keyed by task id. It is a batch for the same reason CompletedSubtaskCounter is - a row's
// details render from the ledger now, and one read per row would turn a single list request into one
// query per task. *repositories.TaskEventRepository satisfies it through ProgressEventsByTask, and
// the wiring passes the same repository the events route reads.
//
// A nil implementation is allowed and leaves every row's details empty, which is the contract the
// other optional dependencies here keep; a wired one that returns no entry for a task leaves that
// row's details empty too, and both are the same answer for a task with no notes.
type TaskProgressEventsByTask interface {
	ProgressEventsByTask(ctx context.Context, taskIDs []string) (map[string][]*entities.TaskEvent, error)
}

// TaskListResponse is the response DTO for task list operations.
type TaskListResponse struct {
	Tasks          []*TaskResponse
	Count          int
	FiltersApplied *entities.OrderedMap[any]
	Query          *string
}

// TaskListResponseFromDomainList mirrors from_domain_list. Python uses a set for
// the branch IDs (order unspecified); Go keeps first-seen order.
func TaskListResponseFromDomainList(ctx context.Context, tasks []*entities.Task,
	gitBranchRepository GitBranchBatchRepository, taskRepository CompletedSubtaskCounter,
	progressEvents TaskProgressEventsByTask,
	filtersApplied *entities.OrderedMap[any], query *string) (*TaskListResponse, error) {

	seen := map[string]bool{}
	branchIDs := []string{}
	for _, task := range tasks {
		if task.GitBranchID == nil || !value_objects.PyTruthy(*task.GitBranchID) {
			continue
		}
		id := *task.GitBranchID
		if !seen[id] {
			seen[id] = true
			branchIDs = append(branchIDs, id)
		}
	}

	branchToProject := map[string]string{}
	if gitBranchRepository != nil && len(branchIDs) > 0 {
		branches := gitBranchRepository.FindByIDs(ctx, branchIDs)
		for _, branchID := range branches.Keys() {
			branch, _ := branches.Get(branchID)
			branchToProject[branchID] = branch.ProjectID
		}
	}

	taskIDs := make([]string, 0, len(tasks))
	for _, task := range tasks {
		taskIDs = append(taskIDs, taskIDString(task))
	}
	completedCounts := map[string]int{}
	if taskRepository != nil && len(taskIDs) > 0 {
		counts, err := taskRepository.GetCompletedSubtaskCounts(ctx, taskIDs)
		if err == nil {
			completedCounts = counts
		}
	}

	// Every row's details render from the ledger, so the notes are read ONCE for the whole page -
	// the same shape as the counts above and for the same reason. Without this the list is the one
	// surface where O1c's move off the column was not carried through, and every row's details is
	// empty while the task dialog shows the notes.
	notesByTask := map[string][]*entities.TaskEvent{}
	if progressEvents != nil && len(taskIDs) > 0 {
		notes, err := progressEvents.ProgressEventsByTask(ctx, taskIDs)
		if err != nil {
			return nil, err
		}
		notesByTask = notes
	}

	taskResponses := make([]*TaskResponse, 0, len(tasks))
	for _, task := range tasks {
		var projectID *string
		if task.GitBranchID != nil && value_objects.PyTruthy(*task.GitBranchID) {
			if pid, ok := branchToProject[*task.GitBranchID]; ok {
				p := pid
				projectID = &p
			}
		}
		completed := completedCounts[taskIDString(task)]
		resp, err := TaskResponseFromDomain(ctx, task, nil, notesByTask[taskIDString(task)], nil, nil, projectID, &completed)
		if err != nil {
			return nil, err
		}
		taskResponses = append(taskResponses, resp)
	}

	return &TaskListResponse{
		Tasks:          taskResponses,
		Count:          len(taskResponses),
		FiltersApplied: filtersApplied,
		Query:          query,
	}, nil
}

func taskIDString(task *entities.Task) string {
	if task.ID == nil {
		return "None"
	}
	return task.ID.Value
}
