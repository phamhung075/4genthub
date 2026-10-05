package subtask

import "agenthub/fastmcp/task_management/domain/entities"

// SubtaskResponse is the response DTO containing subtask information.
type SubtaskResponse struct {
	TaskID                  string
	Subtask                 *entities.OrderedMap[any]
	Progress                *entities.OrderedMap[any]
	AgentInheritanceApplied bool
	InheritedAssignees      []string
}

// ToDict mirrors to_dict(include_parent_id=False); the flag is unused.
func (r *SubtaskResponse) ToDict(includeParentID bool) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", r.TaskID)
	m.Set("subtask", r.Subtask)
	m.Set("progress", r.Progress)
	if r.AgentInheritanceApplied {
		m.Set("agent_inheritance_applied", r.AgentInheritanceApplied)
		m.Set("inherited_assignees", r.InheritedAssignees)
	}
	return m
}
