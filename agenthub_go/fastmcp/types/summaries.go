package types

// Summary DTOs - Lightweight objects for list views (Python types/summaries.py).
// Matches frontend types in taskTypes.ts.

import "agenthub/fastmcp/task_management/domain/entities"

// TaskSummaryDTO matches the frontend TaskSummary interface.
type TaskSummaryDTO struct {
	ID              string
	Title           string
	Status          string
	Priority        string
	SubtaskCount    int
	AssigneesCount  int
	Assignees       []string
	HasDependencies bool
	DependencyCount *int
	HasContext      bool
	GitBranchID     *string
	ProjectID       *string
	CreatedAt       *string
	UpdatedAt       *string
}

func (d *TaskSummaryDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"title", d.Title,
		"status", d.Status,
		"priority", d.Priority,
		"subtask_count", d.SubtaskCount,
		"assignees_count", d.AssigneesCount,
		"assignees", dtoStrList(d.Assignees),
		"has_dependencies", d.HasDependencies,
		"dependency_count", dtoInt(d.DependencyCount),
		"has_context", d.HasContext,
		"git_branch_id", dtoOpt(d.GitBranchID),
		"project_id", dtoOpt(d.ProjectID),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
	)
}

// SubtaskSummaryDTO matches the frontend SubtaskSummary interface.
type SubtaskSummaryDTO struct {
	ID                 string
	TaskID             string
	Title              string
	Status             string
	Priority           string
	AssigneesCount     int
	Assignees          []string
	ProgressPercentage *int
	CreatedAt          *string
	UpdatedAt          *string
}

func (d *SubtaskSummaryDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"task_id", d.TaskID,
		"title", d.Title,
		"status", d.Status,
		"priority", d.Priority,
		"assignees_count", d.AssigneesCount,
		"assignees", dtoStrList(d.Assignees),
		"progress_percentage", dtoInt(d.ProgressPercentage),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
	)
}

// BranchSummaryDTO matches the frontend BranchSummary interface.
type BranchSummaryDTO struct {
	ID                 string
	ProjectID          string
	Name               string
	GitBranchName      *string
	Status             *string
	Priority           *string
	TaskCount          int
	CompletedTasks     int
	InProgressTasks    int
	BlockedTasks       int
	TodoTasks          int
	ProgressPercentage int
	LastActivity       *string
	HasUrgentTasks     *bool
	IsCompleted        *bool
	TaskCounts         any
}

func (d *BranchSummaryDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"project_id", d.ProjectID,
		"name", d.Name,
		"git_branch_name", dtoOpt(d.GitBranchName),
		"status", dtoOpt(d.Status),
		"priority", dtoOpt(d.Priority),
		"task_count", d.TaskCount,
		"completed_tasks", d.CompletedTasks,
		"in_progress_tasks", d.InProgressTasks,
		"blocked_tasks", d.BlockedTasks,
		"todo_tasks", d.TodoTasks,
		"progress_percentage", d.ProgressPercentage,
		"last_activity", dtoOpt(d.LastActivity),
		"has_urgent_tasks", dtoBool(d.HasUrgentTasks),
		"is_completed", dtoBool(d.IsCompleted),
		"task_counts", d.TaskCounts,
	)
}

// ProjectSummaryDTO matches the frontend ProjectSummary interface. Field names
// branchCount/totalTasks/completedTasks are Python's (aliases equal the names).
type ProjectSummaryDTO struct {
	ID             string
	Name           string
	Description    *string
	BranchCount    int
	TotalTasks     int
	CompletedTasks int
}

func (d *ProjectSummaryDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"name", d.Name,
		"description", dtoOpt(d.Description),
		"branchCount", d.BranchCount,
		"totalTasks", d.TotalTasks,
		"completedTasks", d.CompletedTasks,
	)
}
