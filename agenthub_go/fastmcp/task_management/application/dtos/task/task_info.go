package task

import (
	"agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskInfo is information about a task from tasks.json.
type TaskInfo struct {
	ID                  int
	Title               string
	Description         string
	Status              value_objects.TaskStatus
	Dependencies        []int
	Priority            value_objects.Priority
	Details             string
	TestStrategy        string
	EstimatedEffort     string
	ActualEffort        *string
	Assignees           []string
	Labels              []string
	DueDate             string
	CodeContextPaths    []string
	ComplexityScore     int
	RecommendedSubtasks int
	Subtasks            []subtask.SubtaskInfo
}

func taskStatusAsDict(s value_objects.TaskStatus) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("value", s.Value)
	return m
}

func taskPriorityAsDict(p value_objects.Priority) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("value", p.Value)
	return m
}

// ToDict mirrors to_dict: asdict(self) with top-level status/priority replaced
// by .value (nested subtask status/priority stay as {"value": ...} dicts).
func (t TaskInfo) ToDict() *entities.OrderedMap[any] {
	var actualEffort any
	if t.ActualEffort != nil {
		actualEffort = *t.ActualEffort
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", t.ID)
	m.Set("title", t.Title)
	m.Set("description", t.Description)
	m.Set("status", taskStatusAsDict(t.Status))
	m.Set("dependencies", append([]int{}, t.Dependencies...))
	m.Set("priority", taskPriorityAsDict(t.Priority))
	m.Set("details", t.Details)
	m.Set("test_strategy", t.TestStrategy)
	m.Set("estimated_effort", t.EstimatedEffort)
	m.Set("actual_effort", actualEffort)
	m.Set("assignees", append([]string{}, t.Assignees...))
	m.Set("labels", append([]string{}, t.Labels...))
	m.Set("due_date", t.DueDate)
	m.Set("code_context_paths", append([]string{}, t.CodeContextPaths...))
	m.Set("complexity_score", t.ComplexityScore)
	m.Set("recommended_subtasks", t.RecommendedSubtasks)
	nested := make([]any, 0, len(t.Subtasks))
	for _, s := range t.Subtasks {
		nested = append(nested, subtask.SubtaskInfoAsDict(s))
	}
	m.Set("subtasks", nested)
	m.Set("status", t.Status.Value)
	m.Set("priority", t.Priority.Value)
	return m
}
