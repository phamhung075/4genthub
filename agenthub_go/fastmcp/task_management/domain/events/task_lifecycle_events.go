package events

// TaskCreatedEvent: Event raised when a task is created
type TaskCreatedEvent struct {
	BaseDomainEvent
	TaskID    any      `dict:"task_id"` // string, or a value_objects.TaskId (serialized as {"value": id})
	BranchID  string   `dict:"branch_id"`
	Title     string   `dict:"title"`
	Status    string   `dict:"status"`
	Priority  string   `dict:"priority"`
	Assignees []string `dict:"assignees"`
}

// NewTaskCreatedEvent applies the Python field defaults.
func NewTaskCreatedEvent() TaskCreatedEvent {
	e := TaskCreatedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	e.Assignees = []string{}
	return e
}

func (e TaskCreatedEvent) EventType() string { return "TaskCreatedEvent" }

func (e TaskCreatedEvent) ToDict() map[string]any { return EventToDict(e, "TaskCreatedEvent") }

// TaskUpdatedEvent: Event raised when a task is updated
type TaskUpdatedEvent struct {
	BaseDomainEvent
	TaskID      any            `dict:"task_id"` // string, or a value_objects.TaskId (serialized as {"value": id})
	BranchID    string         `dict:"branch_id"`
	OldStatus   *string        `dict:"old_status"`
	NewStatus   *string        `dict:"new_status"`
	OldBranchID *string        `dict:"old_branch_id"`
	NewBranchID *string        `dict:"new_branch_id"`
	Changes     map[string]any `dict:"changes"`
}

// NewTaskUpdatedEvent applies the Python field defaults.
func NewTaskUpdatedEvent() TaskUpdatedEvent {
	e := TaskUpdatedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	e.Changes = map[string]any{}
	return e
}

func (e TaskUpdatedEvent) EventType() string { return "TaskUpdatedEvent" }

func (e TaskUpdatedEvent) ToDict() map[string]any { return EventToDict(e, "TaskUpdatedEvent") }

// TaskDeletedEvent: Event raised when a task is deleted
type TaskDeletedEvent struct {
	BaseDomainEvent
	TaskID   string `dict:"task_id"`
	BranchID string `dict:"branch_id"`
	Status   string `dict:"status"`
	Title    string `dict:"title"`
}

// NewTaskDeletedEvent applies the Python field defaults.
func NewTaskDeletedEvent() TaskDeletedEvent {
	e := TaskDeletedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e TaskDeletedEvent) EventType() string { return "TaskDeletedEvent" }

func (e TaskDeletedEvent) ToDict() map[string]any { return EventToDict(e, "TaskDeletedEvent") }

// TaskStatusChangedEvent: Event raised when task status changes
type TaskStatusChangedEvent struct {
	BaseDomainEvent
	TaskID    string `dict:"task_id"`
	BranchID  string `dict:"branch_id"`
	OldStatus string `dict:"old_status"`
	NewStatus string `dict:"new_status"`
}

// NewTaskStatusChangedEvent applies the Python field defaults.
func NewTaskStatusChangedEvent() TaskStatusChangedEvent {
	e := TaskStatusChangedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e TaskStatusChangedEvent) EventType() string { return "TaskStatusChangedEvent" }

func (e TaskStatusChangedEvent) ToDict() map[string]any {
	return EventToDict(e, "TaskStatusChangedEvent")
}

// TaskCompletedEvent: Event raised when a task is completed.
type TaskCompletedEvent struct {
	BaseDomainEvent
	TaskID            string   `dict:"task_id"`
	BranchID          string   `dict:"branch_id"`
	Title             string   `dict:"title"`
	CompletionSummary string   `dict:"completion_summary"`
	TestingNotes      *string  `dict:"testing_notes"`
	CompletedBy       *string  `dict:"completed_by"`
	TimeSpentMinutes  *int     `dict:"time_spent_minutes"`
	InsightsFound     []string `dict:"insights_found"`
}

// NewTaskCompletedEvent applies the Python field defaults.
func NewTaskCompletedEvent() TaskCompletedEvent {
	e := TaskCompletedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	e.InsightsFound = []string{}
	return e
}

func (e TaskCompletedEvent) EventType() string { return "TaskCompletedEvent" }

func (e TaskCompletedEvent) ToDict() map[string]any { return EventToDict(e, "TaskCompletedEvent") }

// TaskRetrievedEvent: Event raised when a task is retrieved from repository
type TaskRetrievedEvent struct {
	BaseDomainEvent
	TaskID   string  `dict:"task_id"`
	BranchID *string `dict:"branch_id"`
}

// NewTaskRetrievedEvent applies the Python field defaults.
func NewTaskRetrievedEvent() TaskRetrievedEvent {
	e := TaskRetrievedEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e TaskRetrievedEvent) EventType() string { return "TaskRetrievedEvent" }

func (e TaskRetrievedEvent) ToDict() map[string]any { return EventToDict(e, "TaskRetrievedEvent") }

// TaskMovedToBranchEvent: Event raised when task is moved to a different branch
type TaskMovedToBranchEvent struct {
	BaseDomainEvent
	TaskID      string `dict:"task_id"`
	OldBranchID string `dict:"old_branch_id"`
	NewBranchID string `dict:"new_branch_id"`
}

// NewTaskMovedToBranchEvent applies the Python field defaults.
func NewTaskMovedToBranchEvent() TaskMovedToBranchEvent {
	e := TaskMovedToBranchEvent{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e TaskMovedToBranchEvent) EventType() string { return "TaskMovedToBranchEvent" }

func (e TaskMovedToBranchEvent) ToDict() map[string]any {
	return EventToDict(e, "TaskMovedToBranchEvent")
}

// Aliases kept by events/__init__.py for task_events.py consumers: the plain
// names resolve to the standardized *Event types.
type (
	TaskCreated   = TaskCreatedEvent
	TaskUpdated   = TaskUpdatedEvent
	TaskDeleted   = TaskDeletedEvent
	TaskCompleted = TaskCompletedEvent
	TaskRetrieved = TaskRetrievedEvent
)
