package task

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskListItemResponse is the minimal task response for list operations.
type TaskListItemResponse struct {
	ID                 string
	Title              string
	Status             string
	Priority           string
	ProgressPercentage any
	Labels             []string
	DueDate            *string
	UpdatedAt          *time.Time
	HasDependencies    bool
	IsBlocked          bool
}

// NewTaskListItemResponse mirrors the Python __init__: labels are truncated to
// the first three and has_dependencies is bool(dependencies). assignees is
// accepted but not stored (as in Python).
func NewTaskListItemResponse(id, title, status, priority string, progressPercentage any,
	assignees, labels []string, dueDate *string, updatedAt *time.Time, dependencies []string) *TaskListItemResponse {
	if progressPercentage == nil {
		progressPercentage = 0
	}
	storedLabels := []string{}
	if len(labels) > 0 {
		n := len(labels)
		if n > 3 {
			n = 3
		}
		storedLabels = append(storedLabels, labels[:n]...)
	}
	return &TaskListItemResponse{
		ID:                 id,
		Title:              title,
		Status:             status,
		Priority:           priority,
		ProgressPercentage: progressPercentage,
		Labels:             storedLabels,
		DueDate:            dueDate,
		UpdatedAt:          updatedAt,
		HasDependencies:    len(dependencies) > 0,
		IsBlocked:          false,
	}
}

// TaskListItemResponseFromTaskResponse mirrors from_task_response.
func TaskListItemResponseFromTaskResponse(task *TaskResponse) *TaskListItemResponse {
	return NewTaskListItemResponse(task.ID, task.Title, task.Status, task.Priority,
		task.ProgressPercentage, task.Assignees, task.Labels, task.DueDate, task.UpdatedAt, task.Dependencies)
}

// ToDict mirrors to_dict.
func (r *TaskListItemResponse) ToDict() *entities.OrderedMap[any] {
	var dueDate, updatedAt any
	if r.DueDate != nil {
		dueDate = *r.DueDate
	}
	if r.UpdatedAt != nil {
		updatedAt = value_objects.IsoFormat(*r.UpdatedAt)
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", r.ID)
	m.Set("title", r.Title)
	m.Set("status", r.Status)
	m.Set("priority", r.Priority)
	m.Set("progress_percentage", r.ProgressPercentage)
	m.Set("labels", append([]string{}, r.Labels...))
	m.Set("due_date", dueDate)
	m.Set("updated_at", updatedAt)
	m.Set("has_dependencies", r.HasDependencies)
	m.Set("is_blocked", r.IsBlocked)
	return m
}
