package subtask

import (
	"fmt"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateSubtaskRequest is the request DTO for creating a new subtask.
type CreateSubtaskRequest struct {
	TaskID      string
	Title       string
	Description *string
	Status      *string
	Priority    *string
	Assignees   []string
}

// NewCreateSubtaskRequest applies the Python defaults status="todo" and
// priority="medium" and then validates.
func NewCreateSubtaskRequest(r CreateSubtaskRequest) (*CreateSubtaskRequest, error) {
	if r.Status == nil {
		todo := "todo"
		r.Status = &todo
	}
	if r.Priority == nil {
		medium := "medium"
		r.Priority = &medium
	}
	if err := r.Validate(); err != nil {
		return nil, err
	}
	return &r, nil
}

// Validate mirrors CreateSubtaskRequest.validate.
func (r *CreateSubtaskRequest) Validate() error {
	if r.TaskID == "" {
		return &value_objects.ValueError{Msg: "task_id is required"}
	}
	if r.Title == "" {
		return &value_objects.ValueError{Msg: "title is required"}
	}
	statusRepr := "None"
	if r.Status != nil {
		statusRepr = *r.Status
	}
	if statusRepr != "todo" && statusRepr != "in_progress" && statusRepr != "done" {
		return &value_objects.ValueError{Msg: fmt.Sprintf("Invalid status: %s", statusRepr)}
	}
	return nil
}
