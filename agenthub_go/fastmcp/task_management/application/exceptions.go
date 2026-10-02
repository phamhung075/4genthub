// Package application ports task_management/application/exceptions.py.
//
// Python exception classes map to Go structs that embed their parent and expose
// it through Unwrap, so errors.As(err, &parentPtr) mirrors isinstance checks.
package application

import (
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskManagementException is the base exception for all task management application errors.
type TaskManagementException struct {
	Message string
	Code    string
	Details *entities.OrderedMap[any]
}

func (e *TaskManagementException) Error() string { return e.Message }

// NewTaskManagementException applies the Python defaults: code falls back to the
// class name, an omitted details dict becomes {}.
func NewTaskManagementException(message string, code *string, details *entities.OrderedMap[any]) *TaskManagementException {
	c := ""
	if code != nil {
		c = *code
	}
	if c == "" {
		c = "TaskManagementException"
	}
	if details == nil {
		details = entities.NewOrderedMap[any]()
	}
	return &TaskManagementException{Message: message, Code: c, Details: details}
}

// TaskNotFoundError: a requested task cannot be found.
type TaskNotFoundError struct {
	TaskManagementException
	TaskID any
}

func (e *TaskNotFoundError) Unwrap() error { return &e.TaskManagementException }

func NewTaskNotFoundError(taskID any, details *entities.OrderedMap[any]) *TaskNotFoundError {
	message := fmt.Sprintf("Task with ID '%s' not found", value_objects.PyStr(taskID))
	return &TaskNotFoundError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("TASK_NOT_FOUND"), details),
		TaskID:                  taskID,
	}
}

// SubtaskNotFoundError: a requested subtask cannot be found.
type SubtaskNotFoundError struct {
	TaskManagementException
	SubtaskID any
	TaskID    any
}

func (e *SubtaskNotFoundError) Unwrap() error { return &e.TaskManagementException }

func NewSubtaskNotFoundError(subtaskID, taskID any, details *entities.OrderedMap[any]) *SubtaskNotFoundError {
	var message string
	if value_objects.PyTruthy(taskID) {
		message = fmt.Sprintf("Subtask with ID '%s' not found in task '%s'",
			value_objects.PyStr(subtaskID), value_objects.PyStr(taskID))
	} else {
		message = fmt.Sprintf("Subtask with ID '%s' not found", value_objects.PyStr(subtaskID))
	}
	return &SubtaskNotFoundError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("SUBTASK_NOT_FOUND"), details),
		SubtaskID:               subtaskID,
		TaskID:                  taskID,
	}
}

// ValidationError: input data fails validation.
type ValidationError struct {
	TaskManagementException
	Field *string
	Value any
}

func (e *ValidationError) Unwrap() error { return &e.TaskManagementException }

func NewValidationError(message string, field *string, value any, details *entities.OrderedMap[any]) *ValidationError {
	return &ValidationError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("VALIDATION_ERROR"), details),
		Field:                   field,
		Value:                   value,
	}
}

// DuplicateError: attempting to create a duplicate resource.
type DuplicateError struct {
	TaskManagementException
	Resource   string
	Identifier any
}

func (e *DuplicateError) Unwrap() error { return &e.TaskManagementException }

func NewDuplicateError(resource string, identifier any, details *entities.OrderedMap[any]) *DuplicateError {
	message := fmt.Sprintf("Duplicate %s with identifier '%s'", resource, value_objects.PyStr(identifier))
	return &DuplicateError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("DUPLICATE_ERROR"), details),
		Resource:                resource,
		Identifier:              identifier,
	}
}

// AuthorizationError: the user lacks permission for the requested operation.
type AuthorizationError struct {
	TaskManagementException
	Operation string
	Resource  *string
}

func (e *AuthorizationError) Unwrap() error { return &e.TaskManagementException }

func NewAuthorizationError(operation string, resource *string, details *entities.OrderedMap[any]) *AuthorizationError {
	var message string
	if resource != nil && *resource != "" {
		message = fmt.Sprintf("Not authorized to %s %s", operation, *resource)
	} else {
		message = fmt.Sprintf("Not authorized to %s", operation)
	}
	return &AuthorizationError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("AUTHORIZATION_ERROR"), details),
		Operation:               operation,
		Resource:                resource,
	}
}

// BusinessRuleViolationError: an operation violates business rules.
type BusinessRuleViolationError struct {
	TaskManagementException
	Rule string
}

func (e *BusinessRuleViolationError) Unwrap() error { return &e.TaskManagementException }

func NewBusinessRuleViolationError(rule, message string, details *entities.OrderedMap[any]) *BusinessRuleViolationError {
	return &BusinessRuleViolationError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("BUSINESS_RULE_VIOLATION"), details),
		Rule:                    rule,
	}
}

// ExternalServiceError: an external service call fails.
type ExternalServiceError struct {
	TaskManagementException
	Service   string
	Operation string
}

func (e *ExternalServiceError) Unwrap() error { return &e.TaskManagementException }

func NewExternalServiceError(service, operation, message string, details *entities.OrderedMap[any]) *ExternalServiceError {
	full := fmt.Sprintf("External service '%s' failed during '%s': %s", service, operation, message)
	return &ExternalServiceError{
		TaskManagementException: *NewTaskManagementException(full, strPtr("EXTERNAL_SERVICE_ERROR"), details),
		Service:                 service,
		Operation:               operation,
	}
}

// RepositoryProviderError: the repository provider fails to provide a required repository.
type RepositoryProviderError struct {
	TaskManagementException
}

func (e *RepositoryProviderError) Unwrap() error { return &e.TaskManagementException }

func NewRepositoryProviderError(message string, details *entities.OrderedMap[any]) *RepositoryProviderError {
	return &RepositoryProviderError{
		TaskManagementException: *NewTaskManagementException(message, strPtr("REPOSITORY_PROVIDER_ERROR"), details),
	}
}

func strPtr(s string) *string { return &s }
