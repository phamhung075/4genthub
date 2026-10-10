package task

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateTaskRequest is the request DTO for creating a task.
type CreateTaskRequest struct {
	Title              string
	GitBranchID        string
	Description        *string
	Status             *string
	Priority           *string
	Details            string
	EstimatedEffort    string
	Assignees          []string
	Labels             []string
	AcceptanceCriteria []string
	Scope              []string
	DueDate            *string
	Dependencies       []string
	UserID             *string
}

// NewCreateTaskRequest mirrors CreateTaskRequest.__post_init__: label and
// assignee normalization and a non-fatal effort validation.
func NewCreateTaskRequest(r CreateTaskRequest) (*CreateTaskRequest, error) {
	if r.Labels == nil {
		r.Labels = []string{}
	}
	if r.AcceptanceCriteria == nil {
		r.AcceptanceCriteria = []string{}
	}
	if r.Scope == nil {
		r.Scope = []string{}
	}
	if r.Assignees == nil {
		r.Assignees = []string{}
	}
	if r.Dependencies == nil {
		r.Dependencies = []string{}
	}

	if len(r.Labels) > 0 {
		validated := []string{}
		for _, label := range r.Labels {
			if label == "" {
				continue
			}
			labelStr := value_objects.PyStrip(label)
			if labelStr == "" {
				continue
			}
			if (value_objects.LabelValidator{}).IsValidLabel(labelStr) {
				validated = append(validated, labelStr)
			} else {
				suggestions := value_objects.SuggestLabels(labelStr)
				if len(suggestions) > 0 {
					validated = append(validated, suggestions[0])
				} else {
					validated = append(validated, labelStr)
				}
			}
		}
		r.Labels = validated
	}

	if r.EstimatedEffort != "" {
		// Python catches ValueError/AttributeError and keeps the original value.
		_, _ = value_objects.NewEstimatedEffort(r.EstimatedEffort)
	}

	assignees, err := entities.NormalizeAssignees(r.Assignees)
	if err != nil {
		return nil, err
	}
	r.Assignees = assignees

	return &r, nil
}
