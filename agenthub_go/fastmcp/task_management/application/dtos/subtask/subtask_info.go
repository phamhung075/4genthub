package subtask

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskInfo is information about a subtask from tasks.json.
type SubtaskInfo struct {
	ID              int
	Title           string
	Description     string
	Status          value_objects.TaskStatus
	Assignees       []string
	ProgressNotes   string
	Dependencies    []string
	Priority        value_objects.Priority
	Details         string
	TestStrategy    string
	EstimatedEffort string
	Subtasks        []SubtaskInfo
}

func statusAsDict(s value_objects.TaskStatus) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("value", s.Value)
	return m
}

func priorityAsDict(p value_objects.Priority) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("value", p.Value)
	return m
}

// SubtaskInfoAsDict mirrors dataclasses.asdict: TaskStatus/Priority (frozen
// dataclasses) become {"value": ...} and nested subtasks recurse. It is exported
// because TaskInfo.to_dict asdicts its subtasks the same way.
func SubtaskInfoAsDict(s SubtaskInfo) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", s.ID)
	m.Set("title", s.Title)
	m.Set("description", s.Description)
	m.Set("status", statusAsDict(s.Status))
	m.Set("assignees", append([]string{}, s.Assignees...))
	m.Set("progress_notes", s.ProgressNotes)
	m.Set("dependencies", append([]string{}, s.Dependencies...))
	m.Set("priority", priorityAsDict(s.Priority))
	m.Set("details", s.Details)
	m.Set("test_strategy", s.TestStrategy)
	m.Set("estimated_effort", s.EstimatedEffort)
	nested := make([]any, 0, len(s.Subtasks))
	for _, sub := range s.Subtasks {
		nested = append(nested, SubtaskInfoAsDict(sub))
	}
	m.Set("subtasks", nested)
	return m
}

// ToDict mirrors to_dict: asdict output with status/priority replaced by .value.
func (s SubtaskInfo) ToDict() *entities.OrderedMap[any] {
	m := SubtaskInfoAsDict(s)
	m.Set("status", s.Status.Value)
	m.Set("priority", s.Priority.Value)
	return m
}
