package utils

// Response Formatter Utilities (Python task_management/utils/response_formatter.py).
// Standardized response formatting for MCP controllers.

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResponseStatus is the standard response status code enum.
type ResponseStatus string

const (
	ResponseStatusSuccess ResponseStatus = "success"
	ResponseStatusError   ResponseStatus = "error"
	ResponseStatusWarning ResponseStatus = "warning"
	ResponseStatusPartial ResponseStatus = "partial"
)

// ErrorCodes is the standard error-code enum.
type ErrorCodes string

const (
	ErrorCodeValidation         ErrorCodes = "VALIDATION_ERROR"
	ErrorCodeNotFound           ErrorCodes = "NOT_FOUND"
	ErrorCodeUnauthorized       ErrorCodes = "UNAUTHORIZED"
	ErrorCodeForbidden          ErrorCodes = "FORBIDDEN"
	ErrorCodeInternal           ErrorCodes = "INTERNAL_ERROR"
	ErrorCodeConflict           ErrorCodes = "CONFLICT"
	ErrorCodeRateLimited        ErrorCodes = "RATE_LIMITED"
	ErrorCodeServiceUnavailable ErrorCodes = "SERVICE_UNAVAILABLE"
	ErrorCodeBadRequest         ErrorCodes = "BAD_REQUEST"
	ErrorCodeTimeout            ErrorCodes = "TIMEOUT"
)

// now is datetime.now(UTC) with microsecond precision (overridable in tests).
var now = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// StandardResponseFormatter formats MCP controller responses.
type StandardResponseFormatter struct{}

func timestamp() string { return value_objects.IsoFormat(now()) }

// Success formats a successful response.
func (StandardResponseFormatter) Success(data any, message *string) *entities.OrderedMap[any] {
	if message == nil {
		m := "Operation completed successfully"
		message = &m
	}
	d := entities.NewOrderedMap[any]()
	d.Set("status", string(ResponseStatusSuccess))
	d.Set("message", *message)
	d.Set("data", data)
	d.Set("timestamp", timestamp())
	d.Set("success", true)
	return d
}

// Error formats an error response.
func (StandardResponseFormatter) Error(errorCode ErrorCodes, message string, details *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if details == nil {
		details = entities.NewOrderedMap[any]()
	}
	d := entities.NewOrderedMap[any]()
	d.Set("status", string(ResponseStatusError))
	d.Set("error_code", string(errorCode))
	d.Set("message", message)
	d.Set("details", details)
	d.Set("timestamp", timestamp())
	d.Set("success", false)
	return d
}

// Warning formats a warning response.
func (StandardResponseFormatter) Warning(data any, message *string, warnings []string) *entities.OrderedMap[any] {
	if message == nil {
		m := "Operation completed with warnings"
		message = &m
	}
	if warnings == nil {
		warnings = []string{}
	}
	d := entities.NewOrderedMap[any]()
	d.Set("status", string(ResponseStatusWarning))
	d.Set("message", *message)
	d.Set("data", data)
	d.Set("warnings", warnings)
	d.Set("timestamp", timestamp())
	d.Set("success", true)
	return d
}

// Partial formats a partial success response.
func (StandardResponseFormatter) Partial(data any, message *string, completed, total int) *entities.OrderedMap[any] {
	if message == nil {
		m := "Operation partially completed"
		message = &m
	}
	var percentage any
	if total > 0 {
		percentage = float64(completed) / float64(total) * 100
	} else {
		percentage = 0
	}
	progress := entities.NewOrderedMap[any]()
	progress.Set("completed", completed)
	progress.Set("total", total)
	progress.Set("percentage", percentage)

	d := entities.NewOrderedMap[any]()
	d.Set("status", string(ResponseStatusPartial))
	d.Set("message", *message)
	d.Set("data", data)
	d.Set("progress", progress)
	d.Set("timestamp", timestamp())
	d.Set("success", true)
	return d
}

// ValidationError formats a validation error response.
func (StandardResponseFormatter) ValidationError(errors map[string][]string) *entities.OrderedMap[any] {
	details := entities.NewOrderedMap[any]()
	details.Set("validation_errors", errors)
	return StandardResponseFormatter{}.Error(ErrorCodeValidation, "Validation failed", details)
}

// NotFound formats a not-found error response.
func (StandardResponseFormatter) NotFound(resource, identifier string) *entities.OrderedMap[any] {
	message := resource + " not found"
	if identifier != "" {
		message += " with identifier: " + identifier
	}
	details := entities.NewOrderedMap[any]()
	details.Set("resource", resource)
	details.Set("identifier", identifier)
	return StandardResponseFormatter{}.Error(ErrorCodeNotFound, message, details)
}

// Unauthorized formats an unauthorized error response.
func (StandardResponseFormatter) Unauthorized(message *string) *entities.OrderedMap[any] {
	if message == nil {
		m := "Authentication required"
		message = &m
	}
	return StandardResponseFormatter{}.Error(ErrorCodeUnauthorized, *message, nil)
}

// Forbidden formats a forbidden error response.
func (StandardResponseFormatter) Forbidden(message *string) *entities.OrderedMap[any] {
	if message == nil {
		m := "Access forbidden"
		message = &m
	}
	return StandardResponseFormatter{}.Error(ErrorCodeForbidden, *message, nil)
}
