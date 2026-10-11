package utils

// Centralized error handler (Python interface/utils/error_handler.py).

import (
	"errors"
	"reflect"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ErrorCode is the standardized error-code enum.
type ErrorCode string

const (
	ErrorCodeTaskNotFound           ErrorCode = "TASK_NOT_FOUND"
	ErrorCodeTaskAlreadyExists      ErrorCode = "TASK_ALREADY_EXISTS"
	ErrorCodeTaskCompletionBlocked  ErrorCode = "TASK_COMPLETION_BLOCKED"
	ErrorCodeInvalidTaskStatus      ErrorCode = "INVALID_TASK_STATUS"
	ErrorCodeContextRequired        ErrorCode = "CONTEXT_REQUIRED"
	ErrorCodeContextNotFound        ErrorCode = "CONTEXT_NOT_FOUND"
	ErrorCodeContextAlreadyExists   ErrorCode = "CONTEXT_ALREADY_EXISTS"
	ErrorCodeValidationError        ErrorCode = "VALIDATION_ERROR"
	ErrorCodeMissingRequiredParam   ErrorCode = "MISSING_REQUIRED_PARAMETER"
	ErrorCodeInvalidParameterFormat ErrorCode = "INVALID_PARAMETER_FORMAT"
	ErrorCodeDatabaseError          ErrorCode = "DATABASE_ERROR"
	ErrorCodeConstraintViolation    ErrorCode = "CONSTRAINT_VIOLATION"
	ErrorCodeInternalError          ErrorCode = "INTERNAL_ERROR"
	ErrorCodeOperationNotSupported  ErrorCode = "OPERATION_NOT_SUPPORTED"
)

// SQLAlchemyError mirrors sqlalchemy.exc.SQLAlchemyError for isinstance dispatch.
// (sqlite3.Error has no Go equivalent.)
type SQLAlchemyError struct{ Msg string }

func (e *SQLAlchemyError) Error() string { return e.Msg }

// KeyError mirrors Python's KeyError (str(e) is the repr of the key).
type KeyError struct{ Key any }

func (e *KeyError) Error() string { return value_objects.PyRepr(e.Key) }

// UserFriendlyErrorHandler converts exceptions to user-friendly responses.
type UserFriendlyErrorHandler struct{}

// HandleError mirrors handle_error.
func (UserFriendlyErrorHandler) HandleError(exception error, operation string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if context == nil {
		context = entities.NewOrderedMap[any]()
	}

	var dbErr *SQLAlchemyError
	if errors.As(exception, &dbErr) {
		return (UserFriendlyErrorHandler{}).handleDatabaseError(exception, operation, context)
	}

	var valueErr *value_objects.ValueError
	if errors.As(exception, &valueErr) {
		// "context must be updated" branch: Python does nothing and falls through.
		return (UserFriendlyErrorHandler{}).handleValidationError(exception, operation, context)
	}

	var keyErr *KeyError
	if errors.As(exception, &keyErr) {
		return (UserFriendlyErrorHandler{}).handleMissingParameterError(exception, operation, context)
	}

	errorMessage := strings.ToLower(exception.Error())

	if strings.Contains(errorMessage, "task not found") {
		return (UserFriendlyErrorHandler{}).handleTaskNotFoundError(exception, context)
	}
	if strings.Contains(errorMessage, "incomplete subtasks") {
		return (UserFriendlyErrorHandler{}).handleIncompleteSubtasksError(exception, context)
	}
	if strings.Contains(errorMessage, "validation error") || strings.Contains(errorMessage, "invalid") {
		return (UserFriendlyErrorHandler{}).handleValidationError(exception, operation, context)
	}

	return (UserFriendlyErrorHandler{}).handleGenericError(exception, operation, context)
}

func (UserFriendlyErrorHandler) handleDatabaseError(exception error, operation string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	errorStr := strings.ToLower(exception.Error())

	if strings.Contains(errorStr, "label") && (strings.Contains(errorStr, "timestamp") || strings.Contains(errorStr, "created_at") || strings.Contains(errorStr, "updated_at")) {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Label creation failed: Timestamp constraint violation.")
		d.Set("error_code", string(ErrorCodeConstraintViolation))
		d.Set("explanation", "Labels require UTC-aware timestamps. This is a system error, not a user error.")
		d.Set("recovery_instructions", []any{
			"This error indicates a bug in the system code",
			"The system should automatically use UTC timestamps",
			"You can create the task without labels for now",
		})
		tech := entities.NewOrderedMap[any]()
		tech.Set("issue", "Timestamps must be timezone-aware UTC datetime objects")
		tech.Set("fix", "Use datetime.now(UTC) instead of datetime.now()")
		tech.Set("location", "Label repository or service layer")
		d.Set("technical_details", tech)
		d.Set("workaround", "Create task without labels parameter, add labels later after fix")
		examples := entities.NewOrderedMap[any]()
		examples.Set("create_without_labels", "manage_task(action='create', title='Task', git_branch_id='...', assignees=['@go-dev'])")
		d.Set("examples", examples)
		return d
	}

	if strings.Contains(errorStr, "unique constraint failed") {
		if strings.Contains(errorStr, "label") {
			d := entities.NewOrderedMap[any]()
			d.Set("success", false)
			d.Set("error", "A label with this name already exists.")
			d.Set("error_code", string(ErrorCodeConstraintViolation))
			d.Set("recovery_instructions", []any{
				"Use a different label name",
				"The existing label will be automatically reused for the task",
				"Labels are shared across tasks to maintain consistency",
			})
			examples := entities.NewOrderedMap[any]()
			examples.Set("alternative_names", "Try 'backend-api', 'api-backend', or 'backend-service'")
			d.Set("examples", examples)
			return d
		}
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "A record with this information already exists.")
		d.Set("error_code", string(ErrorCodeConstraintViolation))
		d.Set("recovery_instructions", []any{
			"Check if you're trying to create a duplicate record",
			"Use 'update' action instead of 'create' if the record exists",
			"Verify the unique identifier is correct",
		})
		examples := entities.NewOrderedMap[any]()
		examples.Set("check_existing", "Use action='get' to check if the record already exists")
		examples.Set("update_instead", "Use action='update' with the existing record ID")
		d.Set("examples", examples)
		return d
	}

	if strings.Contains(errorStr, "foreign key constraint failed") {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Referenced record does not exist.")
		d.Set("error_code", string(ErrorCodeConstraintViolation))
		d.Set("recovery_instructions", []any{
			"Verify the referenced ID exists (e.g., task_id, project_id)",
			"Create the referenced record first",
			"Check for typos in the ID parameter",
		})
		examples := entities.NewOrderedMap[any]()
		examples.Set("verify_id", "Use action='get' to verify the referenced record exists")
		examples.Set("create_parent", "Create the parent record before creating dependent records")
		d.Set("examples", examples)
		return d
	}

	if strings.Contains(errorStr, "readonly database") {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Database is temporarily read-only.")
		d.Set("error_code", string(ErrorCodeDatabaseError))
		d.Set("recovery_instructions", []any{
			"Try the operation again in a few seconds",
			"Check if there's ongoing maintenance",
			"Contact support if the problem persists",
		})
		return d
	}

	if strings.Contains(errorStr, "database is locked") {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Database is temporarily busy.")
		d.Set("error_code", string(ErrorCodeDatabaseError))
		d.Set("recovery_instructions", []any{
			"Wait a moment and try again",
			"The system may be processing other requests",
		})
		return d
	}

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Database operation failed.")
	d.Set("error_code", string(ErrorCodeDatabaseError))
	d.Set("recovery_instructions", []any{
		"Try the operation again",
		"Check your parameters are correct",
		"Contact support if the problem persists",
	})
	return d
}

func (UserFriendlyErrorHandler) handleContextRequiredError(exception error, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	taskID := ctxString(context, "task_id", "your-task-id")
	_ = ctxString(context, "project_id", "agenthub")

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Task completion requires context to be created first.")
	d.Set("error_code", string(ErrorCodeContextRequired))
	d.Set("explanation", "Context stores task progress with inheritance from project and global contexts. This ensures work history is preserved with proper organizational structure.")
	d.Set("recovery_instructions", []any{
		"Create context for this task first",
		"Update the context with your progress",
		"Then try completing the task again",
	})
	d.Set("step_by_step_fix", []any{
		ctxStep(1, "Create context", "manage_context(action='create', level='task', context_id='"+taskID+"', data={'title': 'Task Title', 'description': 'Task context'})"),
		ctxStep(2, "Update context status", "manage_context(action='update', level='task', context_id='"+taskID+"', data={'status': 'done'})"),
		ctxStep(3, "Complete task", "manage_task(action='complete', task_id='"+taskID+"', completion_summary='Your summary here')"),
	})
	examples := entities.NewOrderedMap[any]()
	examples.Set("minimal_fix", "manage_context(action='create', level='task', context_id='"+taskID+"', data={'title': 'Task Title'}); manage_task(action='complete', task_id='"+taskID+"', completion_summary='Work completed')")
	d.Set("examples", examples)
	return d
}

func (UserFriendlyErrorHandler) handleTaskNotFoundError(exception error, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	taskID := ctxString(context, "task_id", "the specified task")

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Task '"+taskID+"' was not found.")
	d.Set("error_code", string(ErrorCodeTaskNotFound))
	d.Set("recovery_instructions", []any{
		"Verify the task ID is correct",
		"Check if the task was deleted",
		"Use action='list' to see available tasks",
		"Use action='search' to find tasks by title",
	})
	examples := entities.NewOrderedMap[any]()
	examples.Set("list_tasks", "manage_task(action='list', git_branch_id='your-branch-id')")
	examples.Set("search_tasks", "manage_task(action='search', query='task title keywords')")
	d.Set("examples", examples)
	return d
}

func (UserFriendlyErrorHandler) handleIncompleteSubtasksError(exception error, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	taskID := ctxString(context, "task_id", "your-task-id")

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Cannot complete task while subtasks remain incomplete.")
	d.Set("error_code", string(ErrorCodeTaskCompletionBlocked))
	d.Set("explanation", "All subtasks must be completed before the parent task can be marked as done.")
	d.Set("recovery_instructions", []any{
		"List all subtasks to see which are incomplete",
		"Complete each remaining subtask",
		"Then try completing the parent task again",
	})
	d.Set("step_by_step_fix", []any{
		ctxStep(1, "List subtasks", "manage_subtask(action='list', task_id='"+taskID+"')"),
		ctxStep(2, "Complete each incomplete subtask", "manage_subtask(action='complete', task_id='"+taskID+"', subtask_id='subtask-id', completion_summary='Subtask completed')"),
		ctxStep(3, "Complete parent task", "manage_task(action='complete', task_id='"+taskID+"', completion_summary='All subtasks completed')"),
	})
	return d
}

func (UserFriendlyErrorHandler) handleValidationError(exception error, operation string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	errorMessage := exception.Error()

	if strings.Contains(strings.ToLower(errorMessage), "labels") || strings.Contains(strings.ToLower(errorMessage), "label") {
		if strings.Contains(strings.ToLower(errorMessage), "timestamp") || strings.Contains(strings.ToLower(errorMessage), "utc") {
			d := entities.NewOrderedMap[any]()
			d.Set("success", false)
			d.Set("error", "Label creation failed: System timestamp error.")
			d.Set("error_code", string(ErrorCodeConstraintViolation))
			d.Set("explanation", "The system failed to create UTC-aware timestamps for labels. This is a bug in the system code.")
			d.Set("recovery_instructions", []any{
				"This is not your fault - it's a system bug",
				"You can create the task without labels as a workaround",
				"Report this error to the development team",
			})
			tech := entities.NewOrderedMap[any]()
			tech.Set("issue", "Label timestamps must be UTC-aware")
			tech.Set("expected", "datetime.now(UTC)")
			tech.Set("actual", "datetime.now() (naive datetime)")
			tech.Set("fix_location", "Label repository or service layer needs to add UTC")
			d.Set("technical_details", tech)
			workaround := entities.NewOrderedMap[any]()
			workaround.Set("description", "Create task without labels, add labels later")
			workaround.Set("command", "manage_task(action='create', title='Task', git_branch_id='...', assignees=['@go-dev'])")
			d.Set("workaround", workaround)
			return d
		}
		if strings.Contains(strings.ToLower(errorMessage), "format") || strings.Contains(strings.ToLower(errorMessage), "invalid") {
			d := entities.NewOrderedMap[any]()
			d.Set("success", false)
			d.Set("error", "Invalid labels format. Labels must be an array of strings or comma-separated string.")
			d.Set("error_code", string(ErrorCodeInvalidParameterFormat))
			d.Set("recovery_instructions", []any{
				"Use array format: labels=['tag1', 'tag2', 'tag3']",
				"Or comma-separated string: labels='tag1,tag2,tag3'",
				"Each label should be a short, descriptive keyword",
				"Labels can contain letters, numbers, hyphens, and underscores",
			})
			examples := entities.NewOrderedMap[any]()
			examples.Set("correct_array", "labels=['bug', 'urgent', 'frontend']")
			examples.Set("correct_string", "labels='bug,urgent,frontend'")
			examples.Set("with_hyphens", "labels='api-integration,backend-service,high-priority'")
			examples.Set("incorrect_spaces", "labels='bug urgent frontend' (needs commas!)")
			examples.Set("incorrect_special_chars", "labels=['bug!', 'urgent@'] (special chars not allowed)")
			d.Set("examples", examples)
			d.Set("label_naming_tips", []any{
				"Use lowercase for consistency",
				"Use hyphens to separate words: 'api-integration' not 'apiintegration'",
				"Be specific but concise: 'frontend-bug' not 'frontend'",
				"Common labels: bug, feature, urgent, backend, frontend, api, database, security",
			})
			return d
		}
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Label validation error: "+errorMessage)
		d.Set("error_code", string(ErrorCodeValidationError))
		d.Set("recovery_instructions", []any{
			"Check your label format and names",
			"Labels must be alphanumeric with hyphens/underscores",
			"Use descriptive, concise names",
		})
		examples := entities.NewOrderedMap[any]()
		examples.Set("good_labels", "labels=['bug', 'urgent', 'api-integration', 'backend-service']")
		examples.Set("bad_labels", "labels=['bug!', 'urgent@work', 'fix it now'] (special chars, spaces)")
		d.Set("examples", examples)
		return d
	}

	if strings.Contains(strings.ToLower(errorMessage), "progress_percentage") {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Invalid progress percentage format. Must be an integer between 0-100.")
		d.Set("error_code", string(ErrorCodeInvalidParameterFormat))
		d.Set("recovery_instructions", []any{
			"Use integer values only: progress_percentage=50",
			"Range must be 0-100",
			"Don't include % symbol or quotes",
		})
		examples := entities.NewOrderedMap[any]()
		examples.Set("correct", "progress_percentage=75")
		examples.Set("incorrect_string", "progress_percentage='75'")
		examples.Set("incorrect_symbol", "progress_percentage='75%'")
		d.Set("examples", examples)
		return d
	}

	if strings.Contains(strings.ToLower(errorMessage), "assignees") {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Invalid assignees format. Assignees must be an array of user identifiers.")
		d.Set("error_code", string(ErrorCodeInvalidParameterFormat))
		d.Set("recovery_instructions", []any{
			"Use array format: assignees=['user1', 'user2']",
			"Each assignee should be a valid user identifier",
		})
		examples := entities.NewOrderedMap[any]()
		examples.Set("correct", "assignees=['alice', 'bob']")
		examples.Set("single_user", "assignees=['alice']")
		examples.Set("empty", "assignees=[]")
		d.Set("examples", examples)
		return d
	}

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Invalid parameter format: "+errorMessage)
	d.Set("error_code", string(ErrorCodeValidationError))
	d.Set("recovery_instructions", []any{
		"Check the parameter format matches the expected type",
		"Refer to documentation for correct parameter formats",
		"Use workflow guidance examples for reference",
	})
	return d
}

func (UserFriendlyErrorHandler) handleMissingParameterError(exception error, operation string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	missingParam := strings.Trim(exception.Error(), "'\"")

	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Required parameter '"+missingParam+"' is missing.")
	d.Set("error_code", string(ErrorCodeMissingRequiredParam))
	d.Set("recovery_instructions", []any{
		"Add the required parameter: " + missingParam,
		"Check the function signature for all required parameters",
		"Use workflow guidance examples for complete parameter lists",
	})
	examples := entities.NewOrderedMap[any]()
	examples.Set("with_parameter", "Include "+missingParam+" in your function call")
	d.Set("examples", examples)
	return d
}

func (UserFriendlyErrorHandler) handleGenericError(exception error, operation string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "The "+operation+" could not be completed.")
	d.Set("error_code", string(ErrorCodeInternalError))
	d.Set("recovery_instructions", []any{
		"Try the operation again",
		"Check that all required parameters are provided",
		"Verify your parameters are in the correct format",
		"Contact support if the problem persists",
	})
	tech := entities.NewOrderedMap[any]()
	tech.Set("operation", operation)
	tech.Set("error_type", reflect.TypeOf(exception).String())
	d.Set("technical_details", tech)
	return d
}

func ctxString(context *entities.OrderedMap[any], key, def string) string {
	if v, ok := context.Get(key); ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return def
}

func ctxStep(step int, action, command string) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("step", step)
	d.Set("action", action)
	d.Set("command", command)
	return d
}
