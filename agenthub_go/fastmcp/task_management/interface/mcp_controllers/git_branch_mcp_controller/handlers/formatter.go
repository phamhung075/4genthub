package handlers

// formatter.go declares the minimal view of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py)
// that the git branch handlers use. That module has no Go port yet; the interface
// is declared here and reported as a dependency. `metaMap` mirrors the helper
// pattern used by the ported agent handlers.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ErrorCode mirrors the ErrorCodes constants used by these handlers.
type ErrorCode = string

const (
	ErrorCodeValidation       ErrorCode = "VALIDATION_ERROR"
	ErrorCodeResourceNotFound ErrorCode = "RESOURCE_NOT_FOUND"
	ErrorCodeInvalidOperation ErrorCode = "INVALID_OPERATION"
	ErrorCodeOperationFailed  ErrorCode = "OPERATION_FAILED"
)

// ResponseFormatter mirrors create_success_response/create_error_response.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// MetaMap builds an OrderedMap in the given insertion order from key/value
// pairs (nil values are stored as nil, matching Python dict None values).
func MetaMap(pairs ...any) *entities.OrderedMap[any] {
	return metaMap(pairs...)
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

// listLen returns len(v) for the list-like values Python `.get(key, [])`
// produces; non-list values yield 0.
func listLen(v any) int {
	switch t := v.(type) {
	case nil:
		return 0
	case []any:
		return len(t)
	case []*entities.OrderedMap[any]:
		return len(t)
	case []string:
		return len(t)
	}
	return 0
}

// branchName reads git_branch_name from a branch map.
func branchName(b any) any {
	m, ok := b.(*entities.OrderedMap[any])
	if !ok {
		return nil
	}
	v, _ := m.Get("git_branch_name")
	return v
}

// branchID reads id from a branch map.
func branchID(b any) any {
	m, ok := b.(*entities.OrderedMap[any])
	if !ok {
		return nil
	}
	v, _ := m.Get("id")
	return v
}

// branchListOf normalises the git_branches value to []any.
func branchListOf(v any) []any {
	switch t := v.(type) {
	case nil:
		return nil
	case []any:
		return t
	case []*entities.OrderedMap[any]:
		out := make([]any, len(t))
		for i, e := range t {
			out[i] = e
		}
		return out
	}
	return nil
}
