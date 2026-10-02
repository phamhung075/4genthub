package common

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskContext is the application DTO context for the current development task.
type TaskContext struct {
	ID            string
	Title         string
	Description   string
	Requirements  []string
	CurrentPhase  string
	AssignedRoles []string
	PrimaryRole   string
	ContextData   *entities.OrderedMap[any]
	CreatedAt     time.Time
	UpdatedAt     time.Time
	Progress      TaskProgressInfo
}

// ToDict mirrors to_dict: asdict(self) with created_at/updated_at replaced by
// their isoformat() strings.
func (c TaskContext) ToDict() *entities.OrderedMap[any] {
	var contextData any
	if c.ContextData != nil {
		contextData = c.ContextData
	} else {
		contextData = entities.NewOrderedMap[any]()
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", c.ID)
	m.Set("title", c.Title)
	m.Set("description", c.Description)
	m.Set("requirements", append([]string{}, c.Requirements...))
	m.Set("current_phase", c.CurrentPhase)
	m.Set("assigned_roles", append([]string{}, c.AssignedRoles...))
	m.Set("primary_role", c.PrimaryRole)
	m.Set("context_data", contextData)
	m.Set("created_at", value_objects.IsoFormat(c.CreatedAt))
	m.Set("updated_at", value_objects.IsoFormat(c.UpdatedAt))
	m.Set("progress", c.Progress.ToDict())
	return m
}
