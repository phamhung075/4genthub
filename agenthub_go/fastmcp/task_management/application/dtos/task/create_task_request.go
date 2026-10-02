package task

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResolveLegacyRole resolves legacy role names to current ones.
func ResolveLegacyRole(assignee string) string {
	legacyMapping := map[string]string{
		"coding-agent":            "senior_developer",
		"test-orchestrator-agent": "qa_engineer",
		"system-architect-agent":  "architect",
	}
	if v, ok := legacyMapping[assignee]; ok {
		return v
	}
	return assignee
}

// CreateTaskRequest is the request DTO for creating a task.
type CreateTaskRequest struct {
	Title           string
	GitBranchID     string
	Description     *string
	Status          *string
	Priority        *string
	Details         string
	EstimatedEffort string
	Assignees       []string
	Labels          []string
	DueDate         *string
	Dependencies    []string
	UserID          *string
}

// NewCreateTaskRequest mirrors CreateTaskRequest.__post_init__: label and
// assignee normalization and a non-fatal effort validation.
func NewCreateTaskRequest(r CreateTaskRequest) (*CreateTaskRequest, error) {
	if r.Labels == nil {
		r.Labels = []string{}
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

	if len(r.Assignees) > 0 {
		validated := []string{}
		for _, assignee := range r.Assignees {
			if assignee != "" && value_objects.PyStrip(assignee) != "" {
				resolved := ResolveLegacyRole(assignee)
				if resolved != "" {
					if !strings.HasPrefix(resolved, "@") {
						resolved = "@" + resolved
					}
					validated = append(validated, resolved)
				} else if value_objects.IsValidRole(assignee) {
					if !strings.HasPrefix(assignee, "@") {
						assignee = "@" + assignee
					}
					validated = append(validated, assignee)
				} else if strings.HasPrefix(assignee, "@") {
					validated = append(validated, assignee)
				} else {
					validated = append(validated, assignee)
				}
			}
		}
		r.Assignees = validated
	}

	return &r, nil
}
