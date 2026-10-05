package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// NOTE: the Python module fails at import (`project_id` has no default but follows a
// defaulted field, so the dataclass raises TypeError). The Go port keeps the
// intended shape; every consumer must treat the Python behavior as "unavailable".

// BranchEvent is the base of branch lifecycle events (non-frozen in Python).
type BranchEvent struct {
	BranchID  string
	ProjectID *string
	Timestamp time.Time // Python datetime.utcnow(): naive, rendered without an offset
	UserID    *string
}

// NewBranchEvent mirrors BranchEvent.create: timestamp defaults to utcnow.
func NewBranchEvent() BranchEvent { return BranchEvent{Timestamp: now()} }

func (b BranchEvent) toDict(eventType string) map[string]any {
	return map[string]any{
		"branch_id": b.BranchID, "project_id": strOrNil(b.ProjectID),
		"timestamp": value_objects.IsoFormatNaive(b.Timestamp), "user_id": strOrNil(b.UserID), "event_type": eventType,
	}
}

func intOrNil(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}

// BranchCreatedEvent event.
type BranchCreatedEvent struct {
	BranchEvent
	Name        string
	Description *string
	Status      string
}

func NewBranchCreatedEvent() BranchCreatedEvent {
	return BranchCreatedEvent{BranchEvent: NewBranchEvent(), Status: "active"}
}
func (e BranchCreatedEvent) EventType() string { return "BranchCreatedEvent" }
func (e BranchCreatedEvent) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{"name": e.Name, "description": strOrNil(e.Description), "status": e.Status})
}

// BranchUpdatedEvent event.
type BranchUpdatedEvent struct {
	BranchEvent
	OldName      *string
	NewName      *string
	OldStatus    *string
	NewStatus    *string
	OldTaskCount *int
	NewTaskCount *int
}

func NewBranchUpdatedEvent() BranchUpdatedEvent {
	return BranchUpdatedEvent{BranchEvent: NewBranchEvent()}
}
func (e BranchUpdatedEvent) EventType() string { return "BranchUpdatedEvent" }
func (e BranchUpdatedEvent) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"old_name": strOrNil(e.OldName), "new_name": strOrNil(e.NewName), "old_status": strOrNil(e.OldStatus),
		"new_status": strOrNil(e.NewStatus), "old_task_count": intOrNil(e.OldTaskCount), "new_task_count": intOrNil(e.NewTaskCount)})
}

// BranchDeletedEvent event.
type BranchDeletedEvent struct {
	BranchEvent
	Name            string
	TasksDeleted    int
	SubtasksDeleted int
	ContextsDeleted int
}

func NewBranchDeletedEvent() BranchDeletedEvent {
	return BranchDeletedEvent{BranchEvent: NewBranchEvent()}
}
func (e BranchDeletedEvent) EventType() string { return "BranchDeletedEvent" }
func (e BranchDeletedEvent) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"name": e.Name, "tasks_deleted": e.TasksDeleted, "subtasks_deleted": e.SubtasksDeleted, "contexts_deleted": e.ContextsDeleted})
}

// BranchStatisticsUpdatedEvent event.
type BranchStatisticsUpdatedEvent struct {
	BranchEvent
	TaskCount           int
	CompletedTaskCount  int
	InProgressTaskCount int
	TodoTaskCount       int
	ProgressPercentage  float64
}

func NewBranchStatisticsUpdatedEvent() BranchStatisticsUpdatedEvent {
	return BranchStatisticsUpdatedEvent{BranchEvent: NewBranchEvent()}
}
func (e BranchStatisticsUpdatedEvent) EventType() string { return "BranchStatisticsUpdatedEvent" }
func (e BranchStatisticsUpdatedEvent) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"task_count": e.TaskCount, "completed_task_count": e.CompletedTaskCount,
		"in_progress_task_count": e.InProgressTaskCount, "todo_task_count": e.TodoTaskCount,
		"progress_percentage": e.ProgressPercentage})
}
