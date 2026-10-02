package value_objects

import (
	"sort"
	"strings"
)

// TaskStatusEnum enumerates valid task statuses (Python TaskStatusEnum).
type TaskStatusEnum string

const (
	TaskStatusTodo       TaskStatusEnum = "todo"
	TaskStatusInProgress TaskStatusEnum = "in_progress"
	TaskStatusBlocked    TaskStatusEnum = "blocked"
	TaskStatusReview     TaskStatusEnum = "review"
	TaskStatusTesting    TaskStatusEnum = "testing"
	TaskStatusDone       TaskStatusEnum = "done"
	TaskStatusCancelled  TaskStatusEnum = "cancelled"
	TaskStatusArchived   TaskStatusEnum = "archived"
)

// TaskStatusValues lists every status in declaration order.
var TaskStatusValues = []TaskStatusEnum{
	TaskStatusTodo, TaskStatusInProgress, TaskStatusBlocked, TaskStatusReview,
	TaskStatusTesting, TaskStatusDone, TaskStatusCancelled, TaskStatusArchived,
}

// taskStatusTransitions encodes the workflow: direct TODO→DONE is allowed,
// DONE can reopen to IN_PROGRESS, CANCELLED can reopen to TODO, ARCHIVED is final.
var taskStatusTransitions = map[TaskStatusEnum][]TaskStatusEnum{
	TaskStatusTodo:       {TaskStatusInProgress, TaskStatusCancelled, TaskStatusDone},
	TaskStatusInProgress: {TaskStatusBlocked, TaskStatusReview, TaskStatusTesting, TaskStatusCancelled, TaskStatusDone},
	TaskStatusBlocked:    {TaskStatusInProgress, TaskStatusCancelled},
	TaskStatusReview:     {TaskStatusInProgress, TaskStatusTesting, TaskStatusDone, TaskStatusCancelled},
	TaskStatusTesting:    {TaskStatusInProgress, TaskStatusReview, TaskStatusDone, TaskStatusCancelled},
	TaskStatusDone:       {TaskStatusInProgress},
	TaskStatusCancelled:  {TaskStatusTodo},
	TaskStatusArchived:   {},
}

// TaskStatus is a validated task status value object.
type TaskStatus struct{ Value string }

// NewTaskStatus validates value against the known statuses.
func NewTaskStatus(value string) (TaskStatus, error) {
	if value == "" {
		return TaskStatus{}, valueErrorf("Task status cannot be empty")
	}
	valid := make([]string, len(TaskStatusValues))
	for i, s := range TaskStatusValues {
		if string(s) == value {
			return TaskStatus{value}, nil
		}
		valid[i] = string(s)
	}
	return TaskStatus{}, valueErrorf("Invalid task status: %s. Valid statuses: %s", value, strings.Join(valid, ", "))
}

// TaskStatusFromString trims value and defaults empty input to "todo".
func TaskStatusFromString(value string) (TaskStatus, error) {
	if value == "" {
		return NewTaskStatus("todo")
	}
	return NewTaskStatus(strings.TrimSpace(value))
}

func (s TaskStatus) String() string { return s.Value }

func (s TaskStatus) IsTodo() bool       { return s.Value == string(TaskStatusTodo) }
func (s TaskStatus) IsInProgress() bool { return s.Value == string(TaskStatusInProgress) }
func (s TaskStatus) IsDone() bool       { return s.Value == string(TaskStatusDone) }

// IsCompleted is an alias for IsDone.
func (s TaskStatus) IsCompleted() bool { return s.IsDone() }

// GetValidTransitions returns the statuses reachable from the current one.
func (s TaskStatus) GetValidTransitions() map[string]struct{} {
	out := map[string]struct{}{}
	for _, t := range taskStatusTransitions[TaskStatusEnum(s.Value)] {
		out[string(t)] = struct{}{}
	}
	return out
}

// CanTransitionTo reports whether newStatus is reachable from the current status.
func (s TaskStatus) CanTransitionTo(newStatus string) bool {
	_, ok := s.GetValidTransitions()[newStatus]
	return ok
}

// GetTransitionErrorMessage explains why a transition is (in)valid.
func (s TaskStatus) GetTransitionErrorMessage(targetStatus string) string {
	if s.CanTransitionTo(targetStatus) {
		return "Transition from " + s.Value + " to " + targetStatus + " is valid."
	}
	valid := s.GetValidTransitions()
	if len(valid) == 0 {
		return "Status " + s.Value + " is a final state with no valid transitions."
	}
	names := make([]string, 0, len(valid))
	for k := range valid {
		names = append(names, k)
	}
	sort.Strings(names)
	return "Cannot transition from " + s.Value + " to " + targetStatus + ". Valid transitions from " +
		s.Value + ": " + strings.Join(names, ", ")
}
