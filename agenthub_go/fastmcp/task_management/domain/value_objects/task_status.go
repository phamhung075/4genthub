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
//
// EVERY OPEN STATE CAN REACH BLOCKED (owner ruling, 2026-10-15): a task must end `done` or `blocked`
// after it is created, and the lifecycle sweep enforces that by blocking a task that has stood still
// at critical priority longer than TASK_BLOCK_AFTER. It blocks THROUGH THIS RULE (Task.UpdateStatus),
// so a state with no blocked edge cannot be blocked at all: a stale `todo`, `review` or `testing`
// task would stay critical forever and the sweep would report a refusal every interval. The
// TaskStateTransitionService's own rules table already carried all three edges; this table was the one
// that did not, which is the inconsistency this closes. `done` and `archived` are deliberately NOT
// blockable: a finished task is pruned rather than parked, and `archived` is final.
var taskStatusTransitions = map[TaskStatusEnum][]TaskStatusEnum{
	TaskStatusTodo:       {TaskStatusInProgress, TaskStatusBlocked, TaskStatusCancelled, TaskStatusDone},
	TaskStatusInProgress: {TaskStatusBlocked, TaskStatusReview, TaskStatusTesting, TaskStatusCancelled, TaskStatusDone},
	TaskStatusBlocked:    {TaskStatusInProgress, TaskStatusCancelled},
	TaskStatusReview:     {TaskStatusInProgress, TaskStatusBlocked, TaskStatusTesting, TaskStatusDone, TaskStatusCancelled},
	TaskStatusTesting:    {TaskStatusInProgress, TaskStatusBlocked, TaskStatusReview, TaskStatusDone, TaskStatusCancelled},
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
