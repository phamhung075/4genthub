package exceptions

import (
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskManagementException is the base exception for all task management errors.
type TaskManagementException struct {
	Msg         string
	TypeName    string // Python class name, reported by ToDict
	ErrorCode   string
	Severity    value_objects.ErrorSeverity
	Context     map[string]any
	Recoverable bool
	UserMessage string
}

func (e *TaskManagementException) Error() string { return e.Msg }

// ExceptionOption customizes optional constructor arguments (Python **kwargs).
type ExceptionOption func(*exceptionOptions)

type exceptionOptions struct {
	context     map[string]any
	userMessage string
}

// WithContext supplies the initial context dict (used by the database exceptions).
func WithContext(ctx map[string]any) ExceptionOption {
	return func(o *exceptionOptions) { o.context = ctx }
}

// WithUserMessage supplies a user-friendly message.
func WithUserMessage(m string) ExceptionOption {
	return func(o *exceptionOptions) { o.userMessage = m }
}

func collect(opts []ExceptionOption) exceptionOptions {
	var o exceptionOptions
	for _, f := range opts {
		f(&o)
	}
	return o
}

// newTaskManagementException applies Python defaults: error_code falls back to the
// class name, user_message to message, context to an empty dict.
func newTaskManagementException(typeName, message, errorCode string, severity value_objects.ErrorSeverity,
	context map[string]any, recoverable bool, userMessage string) TaskManagementException {
	if errorCode == "" {
		errorCode = typeName
	}
	if context == nil {
		context = map[string]any{}
	}
	if userMessage == "" {
		userMessage = message
	}
	return TaskManagementException{message, typeName, errorCode, severity, context, recoverable, userMessage}
}

// ToDict converts the exception to a dictionary for serialization.
func (e *TaskManagementException) ToDict() map[string]any {
	return map[string]any{
		"error_code": e.ErrorCode, "message": e.Msg, "user_message": e.UserMessage,
		"severity": string(e.Severity), "recoverable": e.Recoverable, "context": e.Context, "type": e.TypeName,
	}
}

func ctxOrNew(o exceptionOptions) map[string]any {
	if o.context == nil {
		return map[string]any{}
	}
	return o.context
}

// ValidationException: input validation failed.
type ValidationException struct{ TaskManagementException }

func (e *ValidationException) Unwrap() error { return &e.TaskManagementException }

// NewValidationException records field and (stringified) value in the context when set.
func NewValidationException(message string, field string, value any, opts ...ExceptionOption) *ValidationException {
	o := collect(opts)
	ctx := ctxOrNew(o)
	if field != "" {
		ctx["field"] = field
	}
	if value != nil {
		ctx["value"] = value_objects.PyStr(value)
	}
	return &ValidationException{newTaskManagementException("ValidationException", message, "VALIDATION_ERROR",
		value_objects.ErrorSeverityLow, ctx, true, o.userMessage)}
}

// ResourceNotFoundException: a requested resource cannot be found.
type ResourceNotFoundException struct{ TaskManagementException }

func (e *ResourceNotFoundException) Unwrap() error { return &e.TaskManagementException }

func newResourceNotFound(typeName, resourceType, resourceID, message string, o exceptionOptions) TaskManagementException {
	if message == "" {
		message = fmt.Sprintf("%s with id '%s' not found", resourceType, resourceID)
	}
	return newTaskManagementException(typeName, message, strings.ToUpper(resourceType)+"_NOT_FOUND",
		value_objects.ErrorSeverityMedium, map[string]any{"resource_type": resourceType, "resource_id": resourceID}, false, o.userMessage)
}

// NewResourceNotFoundException; an empty message selects the default text.
func NewResourceNotFoundException(resourceType, resourceID, message string, opts ...ExceptionOption) *ResourceNotFoundException {
	return &ResourceNotFoundException{newResourceNotFound("ResourceNotFoundException", resourceType, resourceID, message, collect(opts))}
}

// ResourceAlreadyExistsException: creating a resource that already exists.
type ResourceAlreadyExistsException struct{ TaskManagementException }

func (e *ResourceAlreadyExistsException) Unwrap() error { return &e.TaskManagementException }

func NewResourceAlreadyExistsException(resourceType, resourceID, message string, opts ...ExceptionOption) *ResourceAlreadyExistsException {
	o := collect(opts)
	if message == "" {
		message = fmt.Sprintf("%s with id '%s' already exists", resourceType, resourceID)
	}
	return &ResourceAlreadyExistsException{newTaskManagementException("ResourceAlreadyExistsException", message,
		strings.ToUpper(resourceType)+"_ALREADY_EXISTS", value_objects.ErrorSeverityLow,
		map[string]any{"resource_type": resourceType, "resource_id": resourceID}, false, o.userMessage)}
}

// OperationNotPermittedException: operation not permitted due to business rules.
type OperationNotPermittedException struct{ TaskManagementException }

func (e *OperationNotPermittedException) Unwrap() error { return &e.TaskManagementException }

func NewOperationNotPermittedException(operation, reason, message string, opts ...ExceptionOption) *OperationNotPermittedException {
	o := collect(opts)
	if message == "" {
		message = fmt.Sprintf("Operation '%s' not permitted: %s", operation, reason)
	}
	return &OperationNotPermittedException{newTaskManagementException("OperationNotPermittedException", message,
		"OPERATION_NOT_PERMITTED", value_objects.ErrorSeverityMedium,
		map[string]any{"operation": operation, "reason": reason}, false, o.userMessage)}
}

// DatabaseException: base exception for database-related errors.
type DatabaseException struct{ TaskManagementException }

func (e *DatabaseException) Unwrap() error { return &e.TaskManagementException }

func newDatabaseException(typeName, message, operation, table string, o exceptionOptions) TaskManagementException {
	ctx := ctxOrNew(o)
	if operation != "" {
		ctx["operation"] = operation
	}
	if table != "" {
		ctx["table"] = table
	}
	return newTaskManagementException(typeName, message, "DATABASE_ERROR", value_objects.ErrorSeverityHigh, ctx, true, o.userMessage)
}

func NewDatabaseException(message, operation, table string, opts ...ExceptionOption) *DatabaseException {
	return &DatabaseException{newDatabaseException("DatabaseException", message, operation, table, collect(opts))}
}

// DatabaseConnectionException: database connection failed. Python passes
// error_code/severity overrides that DatabaseException pops and discards, so the
// effective code is DATABASE_ERROR and severity HIGH; that behavior is preserved.
type DatabaseConnectionException struct{ DatabaseException }

func (e *DatabaseConnectionException) Unwrap() error { return &e.DatabaseException }

// NewDatabaseConnectionException uses "Failed to connect to database" for an empty message.
func NewDatabaseConnectionException(message string, opts ...ExceptionOption) *DatabaseConnectionException {
	if message == "" {
		message = "Failed to connect to database"
	}
	return &DatabaseConnectionException{DatabaseException{newDatabaseException("DatabaseConnectionException", message, "", "", collect(opts))}}
}

// DatabaseIntegrityException: database integrity constraints violated.
type DatabaseIntegrityException struct{ TaskManagementException }

func (e *DatabaseIntegrityException) Unwrap() error { return &e.TaskManagementException }

func NewDatabaseIntegrityException(message, constraint string, opts ...ExceptionOption) *DatabaseIntegrityException {
	o := collect(opts)
	ctx := ctxOrNew(o)
	if constraint != "" {
		ctx["constraint"] = constraint
	}
	return &DatabaseIntegrityException{newTaskManagementException("DatabaseIntegrityException", message,
		"DATABASE_INTEGRITY_ERROR", value_objects.ErrorSeverityMedium, ctx, false, o.userMessage)}
}

// ConcurrencyException: concurrent operations conflict.
type ConcurrencyException struct{ TaskManagementException }

func (e *ConcurrencyException) Unwrap() error { return &e.TaskManagementException }

func NewConcurrencyException(message, resourceType, resourceID string, opts ...ExceptionOption) *ConcurrencyException {
	o := collect(opts)
	ctx := map[string]any{}
	if resourceType != "" {
		ctx["resource_type"] = resourceType
	}
	if resourceID != "" {
		ctx["resource_id"] = resourceID
	}
	return &ConcurrencyException{newTaskManagementException("ConcurrencyException", message, "CONCURRENCY_ERROR",
		value_objects.ErrorSeverityMedium, ctx, true, o.userMessage)}
}

// ExternalServiceException: external service calls fail.
type ExternalServiceException struct{ TaskManagementException }

func (e *ExternalServiceException) Unwrap() error { return &e.TaskManagementException }

// NewExternalServiceException records status_code in the context when non-zero (Python truthiness).
func NewExternalServiceException(service, message string, statusCode int, opts ...ExceptionOption) *ExternalServiceException {
	o := collect(opts)
	ctx := map[string]any{"service": service}
	if statusCode != 0 {
		ctx["status_code"] = statusCode
	}
	return &ExternalServiceException{newTaskManagementException("ExternalServiceException", message,
		strings.ToUpper(service)+"_SERVICE_ERROR", value_objects.ErrorSeverityMedium, ctx, true, o.userMessage)}
}

// ConfigurationException: configuration is invalid or missing.
type ConfigurationException struct{ TaskManagementException }

func (e *ConfigurationException) Unwrap() error { return &e.TaskManagementException }

func NewConfigurationException(message, configKey string, opts ...ExceptionOption) *ConfigurationException {
	o := collect(opts)
	ctx := map[string]any{}
	if configKey != "" {
		ctx["config_key"] = configKey
	}
	return &ConfigurationException{newTaskManagementException("ConfigurationException", message, "CONFIGURATION_ERROR",
		value_objects.ErrorSeverityCritical, ctx, false, o.userMessage)}
}

// RepositoryError: repository operations fail. As in Python, the REPOSITORY_ERROR
// code is discarded by DatabaseException (effective code DATABASE_ERROR) and the
// context gets operation="repository"; the repository name is stored only when a
// caller-supplied context exists (Python mutates that dict).
type RepositoryError struct{ DatabaseException }

func (e *RepositoryError) Unwrap() error { return &e.DatabaseException }

func NewRepositoryError(message, repository string, opts ...ExceptionOption) *RepositoryError {
	o := collect(opts)
	if o.context != nil && repository != "" {
		// Python mutates the caller's dict, which DatabaseException then reads.
		o.context["repository"] = repository
	}
	return &RepositoryError{DatabaseException{newDatabaseException("RepositoryError", message, "repository", "", o)}}
}

// NotFoundError is a subclass of ResourceNotFoundException (legacy alias class in Python).
type NotFoundError struct{ ResourceNotFoundException }

func (e *NotFoundError) Unwrap() error { return &e.ResourceNotFoundException }

func NewNotFoundError(resourceType, resourceID, message string, opts ...ExceptionOption) *NotFoundError {
	return &NotFoundError{ResourceNotFoundException{newResourceNotFound("NotFoundError", resourceType, resourceID, message, collect(opts))}}
}

// ValidationError is a subclass of ValidationException (legacy alias class in Python).
type ValidationError struct{ ValidationException }

func (e *ValidationError) Unwrap() error { return &e.ValidationException }

func NewValidationError(message string, field string, value any, opts ...ExceptionOption) *ValidationError {
	v := NewValidationException(message, field, value, opts...)
	v.TypeName = "ValidationError"
	return &ValidationError{*v}
}
