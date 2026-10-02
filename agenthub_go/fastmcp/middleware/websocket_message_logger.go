package middleware

import (
	"fmt"
	"reflect"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	vo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ---------------------------------------------------------------------------
// Environment configuration (read at package init, like the Python module).
// ---------------------------------------------------------------------------

var (
	// LogWebsocketMessages is LOG_WEBSOCKET_MESSAGES (default "true").
	LogWebsocketMessages = pyEnvFlag("LOG_WEBSOCKET_MESSAGES", "true")
	// WsLogLevel is WS_LOG_LEVEL (default "info", lowercased).
	WsLogLevel = pyEnvLower("WS_LOG_LEVEL", "info")
	// WsValidationEnabled is WS_VALIDATION_ENABLED (default "true").
	WsValidationEnabled = pyEnvFlag("WS_VALIDATION_ENABLED", "true")
)

// WebSocketEventType is the str Enum WebSocketEventType; the values are the
// same and the underlying type is a string.
type WebSocketEventType string

const (
	WebSocketEventTypeTaskCreated      WebSocketEventType = "task.created"
	WebSocketEventTypeTaskUpdated      WebSocketEventType = "task.updated"
	WebSocketEventTypeTaskDeleted      WebSocketEventType = "task.deleted"
	WebSocketEventTypeTaskCompleted    WebSocketEventType = "task.completed"
	WebSocketEventTypeSubtaskCreated   WebSocketEventType = "subtask.created"
	WebSocketEventTypeSubtaskUpdated   WebSocketEventType = "subtask.updated"
	WebSocketEventTypeSubtaskDeleted   WebSocketEventType = "subtask.deleted"
	WebSocketEventTypeSubtaskCompleted WebSocketEventType = "subtask.completed"
	WebSocketEventTypeBranchUpdated    WebSocketEventType = "branch.updated"
	WebSocketEventTypeProjectUpdated   WebSocketEventType = "project.updated"
	WebSocketEventTypeContextUpdated   WebSocketEventType = "context.updated"
)

// WebSocketMessageValidator validates WebSocket message structure and content.
type WebSocketMessageValidator struct{}

// WebSocketBaseMessageSchema is WebSocketMessageValidator.BASE_MESSAGE_SCHEMA.
var WebSocketBaseMessageSchema = newSchema(
	schemaEntry{"event", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"data", FieldSchema{Type: pyKindDict, Required: true}},
)

// WebSocketTaskEventDataSchema is WebSocketMessageValidator.TASK_EVENT_DATA_SCHEMA.
var WebSocketTaskEventDataSchema = newSchema(
	schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"title", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"status", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"priority", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"assignees", FieldSchema{Type: pyKindList, Required: true}},
	schemaEntry{"subtask_count", FieldSchema{Type: pyKindInt, Required: true}},
	schemaEntry{"completed_subtasks", FieldSchema{Type: pyKindInt, Required: true}},
	schemaEntry{"progress_percentage", FieldSchema{Type: pyKindInt, Required: true}},
	schemaEntry{"progress_count", FieldSchema{Type: pyKindInt, Required: true}},
	schemaEntry{"created_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"updated_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"project_id", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"git_branch_id", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"description", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"details", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"labels", FieldSchema{Type: pyKindList, Required: false}},
)

// WebSocketSubtaskEventDataSchema is WebSocketMessageValidator.SUBTASK_EVENT_DATA_SCHEMA.
var WebSocketSubtaskEventDataSchema = newSchema(
	schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"title", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"status", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"priority", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"parent_task_id", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"assignees", FieldSchema{Type: pyKindList, Required: true}},
	schemaEntry{"progress_percentage", FieldSchema{Type: pyKindInt, Required: true}},
	schemaEntry{"created_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"updated_at", FieldSchema{Type: pyKindStr, Required: true}},
)

// ValidateMessage validates a WebSocket message structure and returns the
// validation error messages (empty if valid).
func (WebSocketMessageValidator) ValidateMessage(message any) []string {
	errors := []string{}

	msg, ok := asOrderedDict(message)
	if !ok {
		errors = append(errors, "Message must be a dictionary")
		return errors
	}

	if !msg.Has("event") {
		errors = append(errors, "Missing required field: 'event'")
	} else if ev, _ := msg.Get("event"); !pyIsInstance(ev, pyKindStr) {
		errors = append(errors, "Field 'event' must be a string")
	}

	if !msg.Has("data") {
		errors = append(errors, "Missing required field: 'data'")
	} else if dt, _ := msg.Get("data"); !isPyDict(dt) {
		errors = append(errors, "Field 'data' must be a dictionary")
		return errors // Can't validate data if it's not a dict
	}

	// Validate data based on event type.
	event := ""
	if ev, ok := msg.Get("event"); ok {
		if s, ok := ev.(string); ok {
			event = s
		}
	}
	dataAny, _ := msg.Get("data")
	data, _ := asOrderedDict(dataAny)
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}

	if strings.HasPrefix(event, "task.") {
		errors = append(errors, (WebSocketMessageValidator{}).validateTaskEventData(data, event)...)
	} else if strings.HasPrefix(event, "subtask.") {
		errors = append(errors, (WebSocketMessageValidator{}).validateSubtaskEventData(data, event)...)
	}

	return errors
}

func (WebSocketMessageValidator) validateTaskEventData(data *entities.OrderedMap[any], event string) []string {
	errors := []string{}

	for _, fieldName := range WebSocketTaskEventDataSchema.Keys() {
		fieldSpec, _ := WebSocketTaskEventDataSchema.Get(fieldName)
		isRequired := fieldSpec.Required
		expectedType := fieldSpec.Type

		value, present := data.Get(fieldName)
		if !present {
			if isRequired {
				errors = append(errors, fmt.Sprintf("Task event '%s': Missing required field '%s'", event, fieldName))
			}
		} else if value == nil {
			if isRequired {
				errors = append(errors, fmt.Sprintf("Task event '%s': Required field '%s' is null", event, fieldName))
			}
		} else if expectedType != "" && !pyIsInstance(value, expectedType) {
			errors = append(errors, fmt.Sprintf("Task event '%s': Field '%s' has wrong type (expected %s, got %s)",
				event, fieldName, expectedType, pyTypeName(value)))
		}
	}

	// Specific validations for critical fields.
	if data.Has("subtask_count") && data.Has("completed_subtasks") {
		subtaskCountAny, _ := data.Get("subtask_count")
		completedSubtasksAny, _ := data.Get("completed_subtasks")
		subtaskCount, ok1 := vo.PyFloat(subtaskCountAny)
		completedSubtasks, ok2 := vo.PyFloat(completedSubtasksAny)
		if ok1 && ok2 && completedSubtasks > subtaskCount {
			errors = append(errors, fmt.Sprintf("Task event '%s': completed_subtasks (%s) exceeds subtask_count (%s)",
				event, vo.PyStr(completedSubtasksAny), vo.PyStr(subtaskCountAny)))
		}
	}

	if data.Has("assignees") {
		assigneesAny, _ := data.Get("assignees")
		if !pyIsInstance(assigneesAny, pyKindList) {
			errors = append(errors, fmt.Sprintf("Task event '%s': assignees must be a list, got %s", event, pyTypeName(assigneesAny)))
		} else if vo.PyTruthy(assigneesAny) { // If not empty, validate format
			rv := reflect.ValueOf(assigneesAny)
			for idx := 0; idx < rv.Len(); idx++ {
				assignee := rv.Index(idx).Interface()
				if !pyIsInstance(assignee, pyKindStr) {
					errors = append(errors, fmt.Sprintf("Task event '%s': assignees[%d] must be string", event, idx))
				}
			}
		}
	}

	return errors
}

func (WebSocketMessageValidator) validateSubtaskEventData(data *entities.OrderedMap[any], event string) []string {
	errors := []string{}

	for _, fieldName := range WebSocketSubtaskEventDataSchema.Keys() {
		fieldSpec, _ := WebSocketSubtaskEventDataSchema.Get(fieldName)
		isRequired := fieldSpec.Required
		expectedType := fieldSpec.Type

		value, present := data.Get(fieldName)
		if !present {
			if isRequired {
				errors = append(errors, fmt.Sprintf("Subtask event '%s': Missing required field '%s'", event, fieldName))
			}
		} else if value == nil {
			if isRequired {
				errors = append(errors, fmt.Sprintf("Subtask event '%s': Required field '%s' is null", event, fieldName))
			}
		} else if expectedType != "" && !pyIsInstance(value, expectedType) {
			errors = append(errors, fmt.Sprintf("Subtask event '%s': Field '%s' has wrong type (expected %s, got %s)",
				event, fieldName, expectedType, pyTypeName(value)))
		}
	}

	return errors
}

// WebSocketMessageLogger logs WebSocket messages with validation.
type WebSocketMessageLogger struct {
	MessageCount     int
	ErrorCount       int
	ValidationErrors []string
}

// NewWebSocketMessageLogger creates a logger with empty counters (the Python
// __init__ logging call is dropped).
func NewWebSocketMessageLogger() *WebSocketMessageLogger {
	return &WebSocketMessageLogger{ValidationErrors: []string{}}
}

// LogMessage logs and optionally validates a WebSocket message, returning the
// validation errors (empty if valid or validation disabled).
func (l *WebSocketMessageLogger) LogMessage(event string, data *entities.OrderedMap[any], userID *string, validate bool) []string {
	l.MessageCount++

	message := entities.NewOrderedMap[any]()
	message.Set("event", event)
	message.Set("data", data)
	message.Set("timestamp", vo.IsoFormat(time.Now().UTC()))

	// Message logging (logger.info with optional debug json.dumps) is dropped.

	validationErrors := []string{}
	if validate && WsValidationEnabled {
		validationErrors = (WebSocketMessageValidator{}).ValidateMessage(message)

		if len(validationErrors) > 0 {
			l.ErrorCount++
			l.ValidationErrors = append(l.ValidationErrors, validationErrors...)
			// logger.error(...) is dropped.
		}
	}

	return validationErrors
}

// GetStats returns logging statistics (key order preserved).
func (l *WebSocketMessageLogger) GetStats() *entities.OrderedMap[any] {
	recent := []string{}
	if len(l.ValidationErrors) > 0 {
		start := len(l.ValidationErrors) - 10
		if start < 0 {
			start = 0
		}
		recent = append(recent, l.ValidationErrors[start:]...)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("total_messages", l.MessageCount)
	out.Set("validation_errors", l.ErrorCount)
	rate := float64(l.ErrorCount) / float64(max(l.MessageCount, 1)) * 100
	out.Set("error_rate", fmt.Sprintf("%.1f%%", rate))
	out.Set("recent_errors", recent)
	return out
}

// globalWebSocketLogger is the module-level _global_logger instance.
var globalWebSocketLogger = NewWebSocketMessageLogger()

// LogWebSocketMessage logs a WebSocket message using the global logger.
func LogWebSocketMessage(event string, data *entities.OrderedMap[any], userID *string, validate bool) []string {
	return globalWebSocketLogger.LogMessage(event, data, userID, validate)
}

// GetWebSocketLogger returns the global WebSocket logger instance.
func GetWebSocketLogger() *WebSocketMessageLogger { return globalWebSocketLogger }

// GetWebSocketStats returns WebSocket logging statistics.
func GetWebSocketStats() *entities.OrderedMap[any] { return globalWebSocketLogger.GetStats() }
