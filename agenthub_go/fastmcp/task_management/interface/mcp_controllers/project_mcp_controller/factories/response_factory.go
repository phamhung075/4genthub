package factories

// Response Factory for Project MCP Controller (Python response_factory.py).

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ErrorCode mirrors the ErrorCodes constants used by this factory.
type ErrorCode = string

const (
	ErrorCodeValidation       ErrorCode = "VALIDATION_ERROR"
	ErrorCodeInvalidOperation ErrorCode = "INVALID_OPERATION"
	ErrorCodeOperationFailed  ErrorCode = "OPERATION_FAILED"
)

// ResponseFormatter mirrors create_error_response of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py),
// which is ported as MCPResponseFormatter in interface/utils/response_formatter.go.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

func metaMap(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// ProjectResponseFactory ports ProjectResponseFactory.
type ProjectResponseFactory struct {
	responseFormatter ResponseFormatter
}

// NewProjectResponseFactory ports __init__(response_formatter).
func NewProjectResponseFactory(responseFormatter ResponseFormatter) *ProjectResponseFactory {
	return &ProjectResponseFactory{responseFormatter: responseFormatter}
}

// CreateMissingFieldError ports create_missing_field_error(field, action).
func (f *ProjectResponseFactory) CreateMissingFieldError(field, action string) *entities.OrderedMap[any] {
	return f.responseFormatter.CreateErrorResponse(
		action,
		"Missing required field: "+field+". Expected: A valid "+field+" string",
		ErrorCodeValidation,
		metaMap("field", field, "hint", "Include '"+field+"' in your request", "action", action),
	)
}

// CreateInvalidActionError ports create_invalid_action_error(invalid_action, valid_actions=None).
func (f *ProjectResponseFactory) CreateInvalidActionError(invalidAction string, validActions []string) *entities.OrderedMap[any] {
	if validActions == nil {
		validActions = []string{
			"create",
			"get",
			"list",
			"update",
			"delete",
			"project_health_check",
			"cleanup_obsolete",
			"validate_integrity",
			"rebalance_agents",
		}
	}

	return f.responseFormatter.CreateErrorResponse(
		"unknown_action",
		"Invalid action",
		ErrorCodeValidation,
		metaMap(
			"field", "action",
			"expected", "One of: "+strings.Join(validActions, ", "),
			"hint", "Invalid action: "+invalidAction+". Use one of the supported actions.",
		),
	)
}
