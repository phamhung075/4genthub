package handlers

// formatter_bridge.go declares the minimal view of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py)
// that the agent handlers use. That module is ported as MCPResponseFormatter in
// interface/utils/response_formatter.go; the interface is declared here and
// reported as a dependency.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ErrorCode mirrors the ErrorCodes constants in interface/utils/response_formatter.py.
type ErrorCode = string

const (
	ErrorCodeMissingField     ErrorCode = "MISSING_FIELD"
	ErrorCodeInvalidAction    ErrorCode = "INVALID_ACTION"
	ErrorCodeInvalidOperation ErrorCode = "INVALID_OPERATION"
	ErrorCodeOperationFailed  ErrorCode = "OPERATION_FAILED"
	ErrorCodeInternalError    ErrorCode = "INTERNAL_ERROR"
)

// ResponseFormatter mirrors create_success_response/create_error_response.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// metaMap builds an OrderedMap in the given insertion order from key/value
// pairs (nil values are stored as nil, matching Python dict None values).
func metaMap(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}
