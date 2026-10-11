package types

// Entity DTOs - Core domain objects (Python types/entities.py).
// Matches frontend types in api.types.ts.

import "agenthub/fastmcp/task_management/domain/entities"

// TaskDTO is the complete task entity for API responses.
type TaskDTO struct {
	ID                 string
	Title              string
	Description        *string
	Status             string
	Priority           string
	Assignees          []string
	AssigneesCount     int
	SubtaskCount       int
	HasDependencies    bool
	DependencyCount    *int
	Dependencies       []string
	HasContext         bool
	ContextID          *string
	ContextData        any
	GitBranchID        *string
	ProjectID          *string
	CreatedAt          *string
	UpdatedAt          *string
	DueDate            *string
	EstimatedEffort    *string
	Labels             []string
	Details            *string
	ProgressPercentage *int
	Subtasks           []*SubtaskDTO
}

func (d *TaskDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"title", d.Title,
		"description", dtoOpt(d.Description),
		"status", d.Status,
		"priority", d.Priority,
		"assignees", dtoStrList(d.Assignees),
		"assignees_count", d.AssigneesCount,
		"subtask_count", d.SubtaskCount,
		"has_dependencies", d.HasDependencies,
		"dependency_count", dtoInt(d.DependencyCount),
		"dependencies", dtoStrList(d.Dependencies),
		"has_context", d.HasContext,
		"context_id", dtoOpt(d.ContextID),
		"context_data", d.ContextData,
		"git_branch_id", dtoOpt(d.GitBranchID),
		"project_id", dtoOpt(d.ProjectID),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
		"due_date", dtoOpt(d.DueDate),
		"estimated_effort", dtoOpt(d.EstimatedEffort),
		"labels", dtoStrList(d.Labels),
		"details", dtoOpt(d.Details),
		"progress_percentage", dtoInt(d.ProgressPercentage),
		"subtasks", dtoModelList(d.Subtasks),
	)
}

// SubtaskDTO is the complete subtask entity for API responses.
type SubtaskDTO struct {
	ID                 string
	TaskID             string
	Title              string
	Description        *string
	Status             string
	Priority           string
	Assignees          []string
	AssigneesCount     int
	ProgressPercentage *int
	CreatedAt          *string
	UpdatedAt          *string
	ProgressNotes      *string
	CompletionSummary  *string
}

func (d *SubtaskDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"task_id", d.TaskID,
		"title", d.Title,
		"description", dtoOpt(d.Description),
		"status", d.Status,
		"priority", d.Priority,
		"assignees", dtoStrList(d.Assignees),
		"assignees_count", d.AssigneesCount,
		"progress_percentage", dtoInt(d.ProgressPercentage),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
		"progress_notes", dtoOpt(d.ProgressNotes),
		"completion_summary", dtoOpt(d.CompletionSummary),
	)
}

// ProjectDTO matches the frontend Project interface.
type ProjectDTO struct {
	ID          string
	Name        string
	Description *string
	CreatedAt   *string
	UpdatedAt   *string
	OwnerID     *string
	Status      *string
	BranchCount *int
	TaskCount   *int
	GitBranchs  *entities.OrderedMap[*BranchDTO]
	Branches    []*BranchDTO
}

func (d *ProjectDTO) ModelDump() *entities.OrderedMap[any] {
	var gitBranchs any
	if d.GitBranchs != nil {
		m := entities.NewOrderedMap[any]()
		for _, k := range d.GitBranchs.Keys() {
			v, _ := d.GitBranchs.Get(k)
			m.Set(k, dtoModelOrNil(v))
		}
		gitBranchs = m
	}
	return dtoMap(
		"id", d.ID,
		"name", d.Name,
		"description", dtoOpt(d.Description),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
		"owner_id", dtoOpt(d.OwnerID),
		"status", dtoOpt(d.Status),
		"branch_count", dtoInt(d.BranchCount),
		"task_count", dtoInt(d.TaskCount),
		"git_branchs", gitBranchs,
		"branches", dtoModelList(d.Branches),
	)
}

// BranchDTO matches the frontend Branch interface.
type BranchDTO struct {
	ID             string
	ProjectID      string
	Name           string
	GitBranchName  string
	Description    *string
	Status         *string
	IsActive       *bool
	CreatedAt      *string
	UpdatedAt      *string
	TaskCount      *int
	CompletedTasks *int
}

func (d *BranchDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"project_id", d.ProjectID,
		"name", d.Name,
		"git_branch_name", d.GitBranchName,
		"description", dtoOpt(d.Description),
		"status", dtoOpt(d.Status),
		"is_active", dtoBool(d.IsActive),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
		"task_count", dtoInt(d.TaskCount),
		"completed_tasks", dtoInt(d.CompletedTasks),
	)
}

// RuleDTO matches the frontend Rule interface.
type RuleDTO struct {
	ID          string
	Name        string
	Description *string
	Category    *string
	Content     *string
	Enabled     *bool
	CreatedAt   *string
	UpdatedAt   *string
}

func (d *RuleDTO) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"id", d.ID,
		"name", d.Name,
		"description", dtoOpt(d.Description),
		"category", dtoOpt(d.Category),
		"content", dtoOpt(d.Content),
		"enabled", dtoBool(d.Enabled),
		"created_at", dtoOpt(d.CreatedAt),
		"updated_at", dtoOpt(d.UpdatedAt),
	)
}
