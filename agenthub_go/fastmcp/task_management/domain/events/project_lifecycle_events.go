package events

// ProjectCreatedEvent: Event raised when a project is created
type ProjectCreatedEvent struct {
	BaseDomainEvent
	ProjectID   string  `dict:"project_id"`
	Name        string  `dict:"name"`
	Description *string `dict:"description"`
	Status      string  `dict:"status"`
}

// NewProjectCreatedEvent applies the Python field defaults.
func NewProjectCreatedEvent() ProjectCreatedEvent {
	e := ProjectCreatedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	e.Status = "active"
	return e
}

func (e ProjectCreatedEvent) EventType() string { return "ProjectCreatedEvent" }

func (e ProjectCreatedEvent) ToDict() map[string]any { return EventToDict(e, "ProjectCreatedEvent") }

// ProjectUpdatedEvent: Event raised when a project is updated
type ProjectUpdatedEvent struct {
	BaseDomainEvent
	ProjectID      string  `dict:"project_id"`
	OldName        *string `dict:"old_name"`
	NewName        *string `dict:"new_name"`
	OldStatus      *string `dict:"old_status"`
	NewStatus      *string `dict:"new_status"`
	OldDescription *string `dict:"old_description"`
	NewDescription *string `dict:"new_description"`
}

// NewProjectUpdatedEvent applies the Python field defaults.
func NewProjectUpdatedEvent() ProjectUpdatedEvent {
	e := ProjectUpdatedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e ProjectUpdatedEvent) EventType() string { return "ProjectUpdatedEvent" }

func (e ProjectUpdatedEvent) ToDict() map[string]any { return EventToDict(e, "ProjectUpdatedEvent") }

// ProjectDeletedEvent: Event raised when a project is deleted
type ProjectDeletedEvent struct {
	BaseDomainEvent
	ProjectID       string `dict:"project_id"`
	Name            string `dict:"name"`
	BranchesDeleted int    `dict:"branches_deleted"`
	TasksDeleted    int    `dict:"tasks_deleted"`
	SubtasksDeleted int    `dict:"subtasks_deleted"`
	ContextsDeleted int    `dict:"contexts_deleted"`
}

// NewProjectDeletedEvent applies the Python field defaults.
func NewProjectDeletedEvent() ProjectDeletedEvent {
	e := ProjectDeletedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e ProjectDeletedEvent) EventType() string { return "ProjectDeletedEvent" }

func (e ProjectDeletedEvent) ToDict() map[string]any { return EventToDict(e, "ProjectDeletedEvent") }

// ProjectStatisticsUpdatedEvent: Event raised when project statistics are updated
type ProjectStatisticsUpdatedEvent struct {
	BaseDomainEvent
	ProjectID                 string  `dict:"project_id"`
	BranchCount               int     `dict:"branch_count"`
	TotalTasks                int     `dict:"total_tasks"`
	CompletedTasks            int     `dict:"completed_tasks"`
	InProgressTasks           int     `dict:"in_progress_tasks"`
	TodoTasks                 int     `dict:"todo_tasks"`
	OverallProgressPercentage float64 `dict:"overall_progress_percentage"`
}

// NewProjectStatisticsUpdatedEvent applies the Python field defaults.
func NewProjectStatisticsUpdatedEvent() ProjectStatisticsUpdatedEvent {
	e := ProjectStatisticsUpdatedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e ProjectStatisticsUpdatedEvent) EventType() string { return "ProjectStatisticsUpdatedEvent" }

func (e ProjectStatisticsUpdatedEvent) ToDict() map[string]any {
	return EventToDict(e, "ProjectStatisticsUpdatedEvent")
}

// ProjectHealthChanged: Event raised when project health metrics change.
type ProjectHealthChanged struct {
	BaseDomainEvent
	ProjectID       string         `dict:"project_id"`
	OldHealthStatus string         `dict:"old_health_status"`
	NewHealthStatus string         `dict:"new_health_status"`
	HealthMetrics   map[string]any `dict:"health_metrics"`
	Reason          *string        `dict:"reason"`
}

// NewProjectHealthChanged applies the Python field defaults.
func NewProjectHealthChanged() ProjectHealthChanged {
	e := ProjectHealthChanged{BaseDomainEvent: NewBaseDomainEvent()}
	e.HealthMetrics = map[string]any{}
	return e
}

func (e ProjectHealthChanged) EventType() string { return "ProjectHealthChanged" }

func (e ProjectHealthChanged) ToDict() map[string]any { return EventToDict(e, "ProjectHealthChanged") }

// ProjectArchived: Event raised when a project is archived
type ProjectArchived struct {
	BaseDomainEvent
	ProjectID  string  `dict:"project_id"`
	Name       string  `dict:"name"`
	ArchivedBy string  `dict:"archived_by"`
	Reason     *string `dict:"reason"`
}

// NewProjectArchived applies the Python field defaults.
func NewProjectArchived() ProjectArchived {
	e := ProjectArchived{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e ProjectArchived) EventType() string { return "ProjectArchived" }

func (e ProjectArchived) ToDict() map[string]any { return EventToDict(e, "ProjectArchived") }
