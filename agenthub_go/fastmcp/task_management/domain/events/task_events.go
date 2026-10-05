package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The legacy task_events.py classes are shadowed by the *Event aliases that
// events/__init__.py exports; they keep the module-prefixed names here.

// TaskEventsDomainEvent is task_events.DomainEvent: a base with an occurred_at defaulting to now.
type TaskEventsDomainEvent struct{ OccurredAt time.Time }

func newLegacyOccurred(t *time.Time) time.Time {
	if t == nil {
		return now()
	}
	return *t
}

// TaskEventsTaskCreated is task_events.TaskCreated.
type TaskEventsTaskCreated struct {
	TaskID     value_objects.TaskId
	Title      string
	CreatedAt  time.Time
	OccurredAt time.Time
}

func NewTaskEventsTaskCreated(taskID value_objects.TaskId, title string, createdAt time.Time, occurredAt *time.Time) TaskEventsTaskCreated {
	return TaskEventsTaskCreated{taskID, title, createdAt, newLegacyOccurred(occurredAt)}
}

// TaskEventsTaskUpdated is task_events.TaskUpdated.
type TaskEventsTaskUpdated struct {
	TaskID     value_objects.TaskId
	FieldName  string
	OldValue   any
	NewValue   any
	UpdatedAt  time.Time
	OccurredAt time.Time
	Metadata   map[string]any
}

func NewTaskEventsTaskUpdated(taskID value_objects.TaskId, fieldName string, oldValue, newValue any, updatedAt time.Time, occurredAt *time.Time, metadata map[string]any) TaskEventsTaskUpdated {
	if metadata == nil {
		metadata = map[string]any{}
	}
	return TaskEventsTaskUpdated{taskID, fieldName, oldValue, newValue, updatedAt, newLegacyOccurred(occurredAt), metadata}
}

// TaskEventsTaskRetrieved is task_events.TaskRetrieved (triggers auto rule generation).
type TaskEventsTaskRetrieved struct {
	TaskID      value_objects.TaskId
	TaskData    map[string]any
	RetrievedAt time.Time
	OccurredAt  time.Time
}

func NewTaskEventsTaskRetrieved(taskID value_objects.TaskId, taskData map[string]any, retrievedAt time.Time, occurredAt *time.Time) TaskEventsTaskRetrieved {
	return TaskEventsTaskRetrieved{taskID, taskData, retrievedAt, newLegacyOccurred(occurredAt)}
}

// TaskEventsTaskDeleted is task_events.TaskDeleted.
type TaskEventsTaskDeleted struct {
	TaskID     value_objects.TaskId
	Title      string
	DeletedAt  time.Time
	OccurredAt time.Time
}

func NewTaskEventsTaskDeleted(taskID value_objects.TaskId, title string, deletedAt time.Time, occurredAt *time.Time) TaskEventsTaskDeleted {
	return TaskEventsTaskDeleted{taskID, title, deletedAt, newLegacyOccurred(occurredAt)}
}
