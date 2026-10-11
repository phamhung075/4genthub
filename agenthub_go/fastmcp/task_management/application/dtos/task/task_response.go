package task

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/application"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GitBranchGetter is task_response.from_domain's lazy repository dependency:
// Python calls git_branch_repository.get_by_id(branch_id). The domain
// repositories.GitBranchRepository interface exposes FindByID instead, so this
// consumer-side interface is declared here.
type GitBranchGetter interface {
	GetByID(ctx context.Context, branchID string) (*entities.GitBranch, error)
}

// TaskResponse is the response DTO for task operations.
type TaskResponse struct {
	ID                 string
	Title              string
	Description        string
	Status             string
	Priority           string
	Details            string
	EstimatedEffort    string
	Assignees          []string
	Labels             []string
	AcceptanceCriteria []string
	Scope              []string
	Dependencies       []string
	Subtasks           []any
	DueDate            *string
	CreatedAt          *time.Time
	UpdatedAt          *time.Time

	GitBranchID *string
	ProjectID   *string
	ContextID   *string
	ContextData *entities.OrderedMap[any]

	DependencyRelationships *DependencyRelationships

	ProgressPercentage any
	CompletedSubtasks  int
}

// NewTaskResponse applies the Python __init__ default: progress_percentage 0 when falsy.
func NewTaskResponse(r TaskResponse) *TaskResponse {
	if r.ProgressPercentage == nil {
		r.ProgressPercentage = 0
	}
	return &r
}

// SubtaskCount is the derived subtask_count property.
func (r *TaskResponse) SubtaskCount() int {
	if len(r.Subtasks) == 0 {
		return 0
	}
	return len(r.Subtasks)
}

// TaskResponseFromDomain mirrors TaskResponse.from_domain.
func TaskResponseFromDomain(ctx context.Context, task *entities.Task, gitBranchRepository GitBranchGetter,
	contextData *entities.OrderedMap[any], dependencyRelationships *DependencyRelationships,
	projectID *string, completedSubtasks *int) (*TaskResponse, error) {

	taskDict, err := task.ToDict()
	if err != nil {
		return nil, err
	}

	if projectID != nil {
		// Fast path: project_id already provided via batch loading.
	} else if gitBranchRepository != nil && value_objects.PyTruthy(taskDict["git_branch_id"]) {
		branchID, _ := taskDict["git_branch_id"].(string)
		gitBranch, err := gitBranchRepository.GetByID(ctx, branchID)
		if err != nil {
			return nil, application.NewRepositoryProviderError(
				fmt.Sprintf("Failed to fetch required project_id: %s", err.Error()), nil)
		}
		if gitBranch != nil {
			pid := gitBranch.ProjectID
			projectID = &pid
		}
	}

	createdAt, err := parseISODateTimeAny(taskDict["created_at"])
	if err != nil {
		return nil, err
	}
	updatedAt, err := parseISODateTimeAny(taskDict["updated_at"])
	if err != nil {
		return nil, err
	}

	details := ""
	if task != nil {
		details = task.GetProgressHistoryText()
	}

	// THE ENTITY IS THE SOURCE OF TRUTH for what an assignee is: normalizeAssignee stores '@<seat_key>'
	// or '@<role>' (entities/task.go:320-337, reached via NormalizeAssignees at :443-462); the picker
	// offers '@<seat_key>' and the client compares against exactly those strings
	// (agenthub-frontend/src/api.ts:366, TaskEditDialog.tsx:169, useTaskFilters.ts:62), and the client's
	// validator WARNS when the '@' is missing (src/utils/responseValidator.ts:148-152). This response
	// used to STRIP the '@' and append '-agent', so a REST-sourced 'go-dev-agent' could not match the
	// picker's '@go-dev' - for ANY name, not just a role ending in -research (row 0adcfe7f).
	//
	// DELIBERATE DEPARTURE FROM THE REFERENCE, and it must not be "restored" as a fidelity fix: the
	// Python stripped and appended at task_response.py:182-190, so this is a behaviour being CORRECTED
	// rather than ported. The stored value is carried through unchanged.
	assignees := []string{}
	if assigneesRaw, ok := taskDict["assignees"].([]string); ok {
		assignees = append(assignees, assigneesRaw...)
	}

	actualCompleted := 0
	if completedSubtasks != nil {
		actualCompleted = *completedSubtasks
	} else {
		actualCompleted = intFromAny(taskDict["completed_subtasks"])
	}

	subtasks := []any{}
	if raw, ok := taskDict["subtasks"].([]string); ok {
		for _, s := range raw {
			subtasks = append(subtasks, s)
		}
	}

	return NewTaskResponse(TaskResponse{
		ID:                      stringFromAny(taskDict["id"]),
		Title:                   stringFromAny(taskDict["title"]),
		Description:             stringFromAny(taskDict["description"]),
		Status:                  stringFromAny(taskDict["status"]),
		Priority:                stringFromAny(taskDict["priority"]),
		Details:                 details,
		EstimatedEffort:         stringFromAny(taskDict["estimatedEffort"]),
		Assignees:               assignees,
		AcceptanceCriteria:      stringSliceFromAny(taskDict["acceptance_criteria"]),
		Scope:                   stringSliceFromAny(taskDict["scope"]),
		Labels:                  stringSliceFromAny(taskDict["labels"]),
		Dependencies:            stringSliceFromAny(taskDict["dependencies"]),
		Subtasks:                subtasks,
		DueDate:                 stringPtrFromAny(taskDict["dueDate"]),
		CreatedAt:               createdAt,
		UpdatedAt:               updatedAt,
		GitBranchID:             stringPtrFromAny(taskDict["git_branch_id"]),
		ProjectID:               projectID,
		ContextID:               stringPtrFromAny(taskDict["context_id"]),
		ContextData:             contextData,
		DependencyRelationships: dependencyRelationships,
		ProgressPercentage:      taskDict["progress_percentage"],
		CompletedSubtasks:       actualCompleted,
	}), nil
}

// ToDict mirrors to_dict. When dependency_relationships is set, Python calls a
// method that does not exist on DependencyRelationships and raises
// AttributeError; Go returns the equivalent error.
func (r *TaskResponse) ToDict() (*entities.OrderedMap[any], error) {
	contextDataSerialized := r.ContextData
	if r.ContextData == nil || r.ContextData.Len() == 0 {
		contextDataSerialized = entities.NewOrderedMap[any]()
	}

	if r.DependencyRelationships != nil {
		return nil, fmt.Errorf("'DependencyRelationships' object has no attribute 'to_dict'")
	}

	assigneesList := r.Assignees
	if assigneesList == nil {
		assigneesList = []string{}
	}

	labels := r.Labels
	if len(labels) == 0 {
		labels = []string{}
	}
	acceptanceCriteria := r.AcceptanceCriteria
	if len(acceptanceCriteria) == 0 {
		acceptanceCriteria = []string{}
	}
	scope := r.Scope
	if len(scope) == 0 {
		scope = []string{}
	}
	dependencies := r.Dependencies
	if len(dependencies) == 0 {
		dependencies = []string{}
	}
	subtasks := r.Subtasks
	if len(subtasks) == 0 {
		subtasks = []any{}
	}

	m := entities.NewOrderedMap[any]()
	m.Set("id", r.ID)
	m.Set("title", r.Title)
	m.Set("description", r.Description)
	m.Set("status", r.Status)
	m.Set("priority", r.Priority)
	m.Set("details", r.Details)
	m.Set("estimatedEffort", r.EstimatedEffort)
	m.Set("assignees", assigneesList)
	m.Set("acceptance_criteria", acceptanceCriteria)
	m.Set("scope", scope)
	m.Set("labels", labels)
	m.Set("dependencies", dependencies)
	m.Set("subtasks", subtasks)
	m.Set("dueDate", anyOrNil(r.DueDate))
	m.Set("created_at", isoOrNil(r.CreatedAt))
	m.Set("updated_at", isoOrNil(r.UpdatedAt))
	m.Set("git_branch_id", anyOrNil(r.GitBranchID))
	m.Set("project_id", anyOrNil(r.ProjectID))
	m.Set("context_id", anyOrNil(r.ContextID))
	m.Set("context_data", contextDataSerialized)
	m.Set("dependency_relationships", nil)
	m.Set("progress_percentage", r.ProgressPercentage)
	m.Set("subtask_count", r.SubtaskCount())
	m.Set("completed_subtasks", r.CompletedSubtasks)
	return m, nil
}

func anyOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

func isoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormat(*t)
}

func parseISODateTimeAny(v any) (*time.Time, error) {
	s, ok := v.(string)
	if !ok {
		return nil, nil
	}
	t, err := value_objects.ParseISO(s)
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func stringFromAny(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	if v == nil {
		return ""
	}
	return value_objects.PyStr(v)
}

func stringPtrFromAny(v any) *string {
	s, ok := v.(string)
	if !ok {
		return nil
	}
	return &s
}

func stringSliceFromAny(v any) []string {
	switch xs := v.(type) {
	case []string:
		return append([]string{}, xs...)
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			out = append(out, stringFromAny(x))
		}
		return out
	}
	return []string{}
}

func intFromAny(v any) int {
	if f, ok := value_objects.PyFloat(v); ok {
		return int(f)
	}
	return 0
}
