package handlers

// formatter.go declares the minimal view of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py)
// used by the subtask handlers. That module is ported as MCPResponseFormatter in
// interface/utils/response_formatter.go; the interface and the error-code
// constants the handlers reference are declared here.

import (
	"context"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// nowUTC mirrors datetime.now(UTC) with microsecond precision.
func nowUTC() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// ErrorCode mirrors the ErrorCodes constants used by the subtask handlers.
type ErrorCode = string

const (
	ErrorCodeValidation       ErrorCode = "VALIDATION_ERROR"
	ErrorCodeOperationFailed  ErrorCode = "OPERATION_FAILED"
	ErrorCodeInvalidOperation ErrorCode = "INVALID_OPERATION"
)

// ResponseFormatter mirrors create_error_response(operation, error, error_code, metadata).
type ResponseFormatter interface {
	CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// ContextFacade is the subset of the parent context facade the handlers call.
// Python invokes context_facade.add_progress(task_id=..., content=..., agent=...).
type ContextFacade interface {
	AddProgress(ctx context.Context, taskID, content, agent string) (*entities.OrderedMap[any], error)
}

// TokenOperationTracker replaces the token-repository tracking that
// _track_token_operation performs through the request-context middleware and the
// request's database session. THE TRACKING IS WHAT IS NOT PORTED - the session
// plumbing exists (infrastructure/database), the per-operation token bookkeeping
// does not - and when nil the background tracking call is a no-op.
type TokenOperationTracker interface {
	TrackTokenOperation(ctx context.Context, operation string) error
}

// omGet returns o[k] or nil, matching dict.get(k).
func omGet(o *entities.OrderedMap[any], key string) any {
	if o == nil {
		return nil
	}
	v, _ := o.Get(key)
	return v
}

// omHas reports whether key is present.
func omHas(o *entities.OrderedMap[any], key string) bool {
	if o == nil {
		return false
	}
	_, ok := o.Get(key)
	return ok
}

// omSuccess reads the boolean "success" field (false when absent/None).
func omSuccess(o *entities.OrderedMap[any]) bool {
	b, _ := omGet(o, "success").(bool)
	return b
}

// omString reads a string field, returning ("", false) when absent/not a string.
func omString(o *entities.OrderedMap[any], key string) (string, bool) {
	s, ok := omGet(o, key).(string)
	return s, ok
}

// omSlice reads a list field as []any (nil when absent).
func omSlice(o *entities.OrderedMap[any], key string) []any {
	v := omGet(o, key)
	switch t := v.(type) {
	case []any:
		return t
	case []string:
		out := make([]any, len(t))
		for i, s := range t {
			out[i] = s
		}
		return out
	}
	return nil
}

// metaMap builds an OrderedMap in the given insertion order from key/value pairs.
func metaMap(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// stringList converts []any to []string, skipping non-strings like Python len() on a list.
func stringList(items []any) []string {
	out := make([]string, 0, len(items))
	for _, it := range items {
		if s, ok := it.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

// intFromAny converts a numeric-ish value to int the way Python would after
// coerce_parameter_types (int, float, or numeric string); ("",false) otherwise.
func intFromAny(v any) (int, bool) {
	switch t := v.(type) {
	case int:
		return t, true
	case int64:
		return int(t), true
	case float64:
		return int(t), true
	case string:
		n := 0
		neg := false
		if t == "" {
			return 0, false
		}
		i := 0
		if t[0] == '-' {
			neg = true
			i = 1
		}
		if i >= len(t) {
			return 0, false
		}
		for ; i < len(t); i++ {
			if t[i] < '0' || t[i] > '9' {
				return 0, false
			}
			n = n*10 + int(t[i]-'0')
		}
		if neg {
			n = -n
		}
		return n, true
	}
	return 0, false
}
