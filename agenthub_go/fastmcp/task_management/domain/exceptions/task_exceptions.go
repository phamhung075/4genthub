package exceptions

import (
	"fmt"
	"regexp"
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskDomainError is the base exception for task domain errors.
type TaskDomainError struct {
	Msg         string
	ErrorCode   string
	Severity    value_objects.ErrorSeverity
	Context     map[string]any
	Recoverable bool
}

func (e *TaskDomainError) Error() string { return e.Msg }

// newTaskDomainError applies the Python defaults: error_code falls back to the
// class name, severity MEDIUM, recoverable true, empty context.
func newTaskDomainError(typeName, message, errorCode string, severity value_objects.ErrorSeverity, context map[string]any, recoverable bool) TaskDomainError {
	if errorCode == "" {
		errorCode = typeName
	}
	if context == nil {
		context = map[string]any{}
	}
	return TaskDomainError{message, errorCode, severity, context, recoverable}
}

func defaultTaskDomainError(typeName, message string) TaskDomainError {
	return newTaskDomainError(typeName, message, "", value_objects.ErrorSeverityMedium, nil, true)
}

var taskNotFoundPattern = regexp.MustCompile(`Task ([\p{L}\p{N}_]+) not found`)

// TaskNotFoundError: a task is not found.
type TaskNotFoundError struct {
	TaskDomainError
	TaskID any
}

func (e *TaskNotFoundError) Unwrap() error { return &e.TaskDomainError }

// NewTaskNotFoundError accepts either a pre-formatted "... not found" message or a raw task ID.
func NewTaskNotFoundError(messageOrTaskID any) *TaskNotFoundError {
	var message string
	var taskID any
	if s, ok := messageOrTaskID.(string); ok && containsNotFound(s) {
		message = s
		if m := taskNotFoundPattern.FindStringSubmatch(s); m != nil {
			taskID = m[1]
		} else {
			taskID = s
		}
	} else {
		taskID = messageOrTaskID
		message = fmt.Sprintf("Task with ID %v not found", messageOrTaskID)
	}
	return &TaskNotFoundError{
		newTaskDomainError("TaskNotFoundError", message, "TASK_NOT_FOUND", value_objects.ErrorSeverityMedium,
			map[string]any{"task_id": taskID}, false),
		taskID,
	}
}

func containsNotFound(s string) bool { return strings.Contains(s, "not found") }

// InvalidTaskStateError: a task operation is invalid for the current state.
type InvalidTaskStateError struct{ TaskDomainError }

func (e *InvalidTaskStateError) Unwrap() error { return &e.TaskDomainError }

func NewInvalidTaskStateError(message string) *InvalidTaskStateError {
	return &InvalidTaskStateError{defaultTaskDomainError("InvalidTaskStateError", message)}
}

// InvalidTaskTransitionError: a task status transition is invalid.
type InvalidTaskTransitionError struct {
	TaskDomainError
	CurrentStatus string
	TargetStatus  string
}

func (e *InvalidTaskTransitionError) Unwrap() error { return &e.TaskDomainError }

func NewInvalidTaskTransitionError(currentStatus, targetStatus string) *InvalidTaskTransitionError {
	msg := fmt.Sprintf("Cannot transition from '%s' to '%s'", currentStatus, targetStatus)
	return &InvalidTaskTransitionError{defaultTaskDomainError("InvalidTaskTransitionError", msg), currentStatus, targetStatus}
}

// AutoRuleGenerationError: auto rule generation failed.
type AutoRuleGenerationError struct {
	TaskDomainError
	OriginalException error
}

func (e *AutoRuleGenerationError) Unwrap() []error {
	return []error{&e.TaskDomainError, e.OriginalException}
}

func NewAutoRuleGenerationError(message string, original error) *AutoRuleGenerationError {
	return &AutoRuleGenerationError{defaultTaskDomainError("AutoRuleGenerationError", message), original}
}

// AgentNotFoundError: an agent is not found.
type AgentNotFoundError struct{ TaskDomainError }

func (e *AgentNotFoundError) Unwrap() error { return &e.TaskDomainError }

func NewAgentNotFoundError(message string) *AgentNotFoundError {
	return &AgentNotFoundError{defaultTaskDomainError("AgentNotFoundError", message)}
}

// ProjectNotFoundError: a project is not found.
type ProjectNotFoundError struct{ TaskDomainError }

func (e *ProjectNotFoundError) Unwrap() error { return &e.TaskDomainError }

func NewProjectNotFoundError(message string) *ProjectNotFoundError {
	return &ProjectNotFoundError{defaultTaskDomainError("ProjectNotFoundError", message)}
}

// TaskValidationError: task validation failed.
type TaskValidationError struct {
	TaskDomainError
	ValidationErrors []string
}

func (e *TaskValidationError) Unwrap() error { return &e.TaskDomainError }

func NewTaskValidationError(message string, validationErrors []string) *TaskValidationError {
	validationErrors = nonNilStrings(validationErrors)
	return &TaskValidationError{
		newTaskDomainError("TaskValidationError", message, "TASK_VALIDATION_ERROR", value_objects.ErrorSeverityMedium,
			map[string]any{"validation_errors": validationErrors}, true),
		validationErrors,
	}
}

// TaskCompletionError: a task cannot be completed due to business rule violations.
type TaskCompletionError struct {
	TaskDomainError
	IncompleteSubtasks []map[string]any
}

func (e *TaskCompletionError) Unwrap() error { return &e.TaskDomainError }

func NewTaskCompletionError(message string, incompleteSubtasks []map[string]any) *TaskCompletionError {
	context := map[string]any{}
	if len(incompleteSubtasks) > 0 {
		context["incomplete_subtasks"] = incompleteSubtasks
		context["incomplete_count"] = len(incompleteSubtasks)
	}
	if incompleteSubtasks == nil {
		incompleteSubtasks = []map[string]any{}
	}
	return &TaskCompletionError{
		newTaskDomainError("TaskCompletionError", message, "SUBTASKS_NOT_COMPLETE", value_objects.ErrorSeverityMedium, context, true),
		incompleteSubtasks,
	}
}

// TaskCreationError: a task cannot be created.
type TaskCreationError struct{ TaskDomainError }

func (e *TaskCreationError) Unwrap() error { return &e.TaskDomainError }

func NewTaskCreationError(message string) *TaskCreationError {
	return &TaskCreationError{defaultTaskDomainError("TaskCreationError", message)}
}

// TaskUpdateError: a task cannot be updated.
type TaskUpdateError struct{ TaskDomainError }

func (e *TaskUpdateError) Unwrap() error { return &e.TaskDomainError }

func NewTaskUpdateError(message string) *TaskUpdateError {
	return &TaskUpdateError{defaultTaskDomainError("TaskUpdateError", message)}
}

// DuplicateTaskError: attempting to create a duplicate task.
type DuplicateTaskError struct{ TaskDomainError }

func (e *DuplicateTaskError) Unwrap() error { return &e.TaskDomainError }

func NewDuplicateTaskError(message string) *DuplicateTaskError {
	return &DuplicateTaskError{defaultTaskDomainError("DuplicateTaskError", message)}
}

// TaskStateTransitionError: a task state transition fails.
type TaskStateTransitionError struct{ TaskDomainError }

func (e *TaskStateTransitionError) Unwrap() error { return &e.TaskDomainError }

func NewTaskStateTransitionError(message string) *TaskStateTransitionError {
	return &TaskStateTransitionError{defaultTaskDomainError("TaskStateTransitionError", message)}
}
