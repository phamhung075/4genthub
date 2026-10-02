package handlers

// Shared helpers for the project handlers.

import "fmt"

// strVal mirrors Python description="" default for a None argument.
func strVal(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// panicMessage renders a recovered value the way f"{e}" would.
func panicMessage(r any) string {
	if err, ok := r.(error); ok {
		return err.Error()
	}
	return fmt.Sprint(r)
}

// pyLen mirrors len(x) for lists and maps.
func pyLen(v any) int {
	switch t := v.(type) {
	case nil:
		return 0
	case []any:
		return len(t)
	case []string:
		return len(t)
	case map[string]any:
		return len(t)
	case interface{ Len() int }:
		return t.Len()
	default:
		return 0
	}
}
