// Package dtos ports task_management/application/dtos/task_dtos.py and
// template_dtos.py.
package dtos

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateTaskDTO is the DTO for creating a new task.
type CreateTaskDTO struct {
	Title           string
	Description     string
	GitBranchID     *string
	Status          *string
	Priority        *string
	Assignees       []string
	Labels          []string
	DueDate         *string
	EstimatedEffort *string
	Details         *string
}

// ToDict mirrors to_dict.
func (d CreateTaskDTO) ToDict() *entities.OrderedMap[any] {
	assignees := d.Assignees
	if len(assignees) == 0 {
		assignees = []string{}
	}
	labels := d.Labels
	if len(labels) == 0 {
		labels = []string{}
	}
	var details any
	if d.Details != nil {
		details = *d.Details
	} else {
		details = ""
	}
	m := entities.NewOrderedMap[any]()
	m.Set("title", d.Title)
	m.Set("description", d.Description)
	m.Set("git_branch_id", stringOrNil(d.GitBranchID))
	m.Set("status", stringOrNil(d.Status))
	m.Set("priority", stringOrNil(d.Priority))
	m.Set("assignees", assignees)
	m.Set("labels", labels)
	m.Set("due_date", stringOrNil(d.DueDate))
	m.Set("estimated_effort", stringOrNil(d.EstimatedEffort))
	m.Set("details", details)
	return m
}

// UpdateTaskDTO is the DTO for updating an existing task.
type UpdateTaskDTO struct {
	TaskID          string
	Title           *string
	Description     *string
	Status          *string
	Priority        *string
	Assignees       []string
	Labels          []string
	DueDate         *string
	EstimatedEffort *string
	Details         *string
	ContextID       *string
}

// ToDict mirrors to_dict: task_id first, then only the fields that are not None.
func (d UpdateTaskDTO) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", d.TaskID)
	if d.Title != nil {
		m.Set("title", *d.Title)
	}
	if d.Description != nil {
		m.Set("description", *d.Description)
	}
	if d.Status != nil {
		m.Set("status", *d.Status)
	}
	if d.Priority != nil {
		m.Set("priority", *d.Priority)
	}
	if d.Assignees != nil {
		m.Set("assignees", d.Assignees)
	}
	if d.Labels != nil {
		m.Set("labels", d.Labels)
	}
	if d.DueDate != nil {
		m.Set("due_date", *d.DueDate)
	}
	if d.EstimatedEffort != nil {
		m.Set("estimated_effort", *d.EstimatedEffort)
	}
	if d.Details != nil {
		m.Set("details", *d.Details)
	}
	if d.ContextID != nil {
		m.Set("context_id", *d.ContextID)
	}
	return m
}

// TaskResponseDTO is the DTO for a task response.
type TaskResponseDTO struct {
	Success  bool
	TaskID   *string
	Message  *string
	TaskData *entities.OrderedMap[any]
	Errors   []string
}

// ToDict mirrors to_dict.
func (d TaskResponseDTO) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", d.Success)
	if d.TaskID != nil {
		m.Set("task_id", *d.TaskID)
	}
	if d.Message != nil {
		m.Set("message", *d.Message)
	}
	if d.TaskData != nil {
		m.Set("task_data", d.TaskData)
	}
	if d.Errors != nil {
		m.Set("errors", d.Errors)
	}
	return m
}

// CompleteTaskDTO is the DTO for completing a task.
type CompleteTaskDTO struct {
	TaskID            string
	CompletionSummary string
	ContextUpdatedAt  *time.Time
}

// ToDict mirrors to_dict.
func (d CompleteTaskDTO) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", d.TaskID)
	m.Set("completion_summary", d.CompletionSummary)
	if d.ContextUpdatedAt != nil {
		m.Set("context_updated_at", value_objects.IsoFormat(*d.ContextUpdatedAt))
	}
	return m
}

func stringOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}
