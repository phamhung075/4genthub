package services

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// MinimalResponseSerializer serializes task and subtask entities with minimal
// redundancy for token optimization
// (Python application/services/minimal_response_serializer.py).
type MinimalResponseSerializer struct{}

// minimalGet looks a key up in a Python-dict-like value.
func minimalGet(full any, key string) (any, bool) {
	switch d := full.(type) {
	case *entities.OrderedMap[any]:
		return d.Get(key)
	case map[string]any:
		v, ok := d[key]
		return v, ok
	}
	return nil, false
}

// minimalTaskFullDict mirrors `task.to_dict() if hasattr(task, "to_dict") else task`.
func minimalTaskFullDict(task any) (any, error) {
	if t, ok := task.(*entities.Task); ok {
		return t.ToDict()
	}
	return task, nil
}

// minimalSubtaskFullDict mirrors `subtask.to_dict(include_parent_id=True)`.
func minimalSubtaskFullDict(subtask any) (any, error) {
	if s, ok := subtask.(*entities.Subtask); ok {
		return s.ToDict(true)
	}
	return subtask, nil
}

// SerializeTaskMinimal serializes a task entity with the essential computed
// properties. `task` may be *entities.Task or a dict-like value.
func (MinimalResponseSerializer) SerializeTaskMinimal(task any, operation string) (*entities.OrderedMap[any], error) {
	full, err := minimalTaskFullDict(task)
	if err != nil {
		return nil, err
	}
	minimal := entities.NewOrderedMap[any]()
	id, _ := minimalGet(full, "id")
	createdAt, _ := minimalGet(full, "created_at")
	updatedAt, _ := minimalGet(full, "updated_at")
	minimal.Set("id", id)
	minimal.Set("created_at", createdAt)
	minimal.Set("updated_at", updatedAt)

	for _, key := range []string{"context_id", "overall_progress", "progress_percentage", "subtask_count", "completed_subtasks", "dependency_count"} {
		if v, ok := minimalGet(full, key); ok {
			minimal.Set(key, v)
		}
	}

	if operation == "create" {
		if v, ok := minimalGet(full, "git_branch_id"); ok {
			minimal.Set("git_branch_id", v)
		}
	}
	if operation == "create" {
		if v, ok := minimalGet(full, "status"); ok {
			minimal.Set("status", v)
		}
		if v, ok := minimalGet(full, "priority"); ok {
			minimal.Set("priority", v)
		}
	}
	return minimal, nil
}

// SerializeSubtaskMinimal serializes a subtask entity with the essential computed
// properties. `subtask` may be *entities.Subtask or a dict-like value.
func (MinimalResponseSerializer) SerializeSubtaskMinimal(subtask any, operation string) (*entities.OrderedMap[any], error) {
	full, err := minimalSubtaskFullDict(subtask)
	if err != nil {
		return nil, err
	}
	minimal := entities.NewOrderedMap[any]()
	id, _ := minimalGet(full, "id")
	title, _ := minimalGet(full, "title")
	description, _ := minimalGet(full, "description")
	status, _ := minimalGet(full, "status")
	parentTaskID, _ := minimalGet(full, "parent_task_id")
	createdAt, _ := minimalGet(full, "created_at")
	updatedAt, _ := minimalGet(full, "updated_at")
	minimal.Set("id", id)
	minimal.Set("title", title)
	minimal.Set("description", description)
	minimal.Set("status", status)
	minimal.Set("task_id", parentTaskID)
	minimal.Set("parent_task_id", parentTaskID)
	minimal.Set("created_at", createdAt)
	minimal.Set("updated_at", updatedAt)

	if v, ok := minimalGet(full, "progress_percentage"); ok {
		minimal.Set("progress_percentage", v)
	}
	if operation == "create" {
		if v, ok := minimalGet(full, "priority"); ok {
			minimal.Set("priority", v)
		}
	}
	return minimal, nil
}

// SerializeTaskListMinimal serializes a task list with moderate optimization.
func (MinimalResponseSerializer) SerializeTaskListMinimal(tasks []any) []*entities.OrderedMap[any] {
	optimized := make([]*entities.OrderedMap[any], 0, len(tasks))
	for _, task := range tasks {
		out := entities.NewOrderedMap[any]()
		for _, key := range []string{"id", "title", "status", "priority", "progress_percentage", "subtask_count", "completed_subtasks", "assignees", "created_at", "updated_at"} {
			v, _ := minimalGet(task, key)
			out.Set(key, v)
		}
		optimized = append(optimized, out)
	}
	return optimized
}

// SerializeSubtaskListMinimal serializes a subtask list with moderate optimization.
func (MinimalResponseSerializer) SerializeSubtaskListMinimal(subtasks []any) []*entities.OrderedMap[any] {
	optimized := make([]*entities.OrderedMap[any], 0, len(subtasks))
	for _, subtask := range subtasks {
		out := entities.NewOrderedMap[any]()
		for _, key := range []string{"id", "title", "status", "priority", "progress_percentage", "assignees", "created_at", "updated_at"} {
			v, _ := minimalGet(subtask, key)
			out.Set(key, v)
		}
		optimized = append(optimized, out)
	}
	return optimized
}

// ShouldUseMinimalSerialization returns true for create/update/complete.
func (MinimalResponseSerializer) ShouldUseMinimalSerialization(operation string) bool {
	switch operation {
	case "create", "update", "complete":
		return true
	}
	return false
}

// GetTokenSavingsEstimate returns the human-readable savings estimate.
func (MinimalResponseSerializer) GetTokenSavingsEstimate(operation string) string {
	switch operation {
	case "create", "update", "complete":
		return "~70-75% reduction (600-800 tokens → 150-200 tokens)"
	case "list", "search":
		return "~40-50% reduction per item"
	}
	return "No optimization (full details needed)"
}
