package subtask

import (
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AddSubtaskRequest is the request DTO for adding a subtask to a task.
type AddSubtaskRequest struct {
	TaskID             any
	Title              string
	Description        string
	Assignees          []string
	AcceptanceCriteria []string
	Scope              []string
	Priority           *string
	Status             *string
	ProgressPercentage *int
}

// NewAddSubtaskRequest mirrors AddSubtaskRequest.__post_init__.
func NewAddSubtaskRequest(r AddSubtaskRequest) (*AddSubtaskRequest, error) {
	if r.Title == "" || value_objects.PyStrip(r.Title) == "" {
		return nil, &value_objects.ValueError{Msg: "Title cannot be empty"}
	}
	if utf8.RuneCountInString(r.Title) > 255 {
		return nil, &value_objects.ValueError{Msg: "Title too long (maximum 255 characters)"}
	}
	if r.Description != "" && utf8.RuneCountInString(r.Description) > 2000 {
		return nil, &value_objects.ValueError{Msg: "Description too long (maximum 2000 characters)"}
	}
	if len(r.Assignees) > 0 {
		for _, assignee := range r.Assignees {
			if assignee == "" || value_objects.PyStrip(assignee) == "" {
				return nil, &value_objects.ValueError{Msg: "Assignee cannot be empty"}
			}
		}
	}
	return &r, nil
}
