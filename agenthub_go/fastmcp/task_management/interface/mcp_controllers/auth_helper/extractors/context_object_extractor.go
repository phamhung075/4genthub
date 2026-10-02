// Package extractors ports
// task_management/interface/mcp_controllers/auth_helper/extractors/context_object_extractor.py.
package extractors

import (
	"reflect"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextObjectExtractor extracts a user ID from various context object types.
type ContextObjectExtractor struct{}

// ExtractUserID mirrors ContextObjectExtractor.extract_user_id. Python uses
// isinstance/hasattr on arbitrary objects; Go mirrors it with a type switch plus
// reflection over the UserID / ID fields, and a "get" lookup for string-keyed maps.
func (ContextObjectExtractor) ExtractUserID(contextObj any) *string {
	if contextObj == nil {
		return nil
	}

	// If it's already a string, return it directly.
	if s, ok := contextObj.(string); ok {
		return &s
	}

	// If it's a dict-like object, try to get user_id key.
	switch m := contextObj.(type) {
	case map[string]any:
		if v, ok := m["user_id"]; ok && v != nil {
			return pyStringPtr(v)
		}
	case *entities.OrderedMap[any]:
		if m != nil {
			if v, ok := m.Get("user_id"); ok && v != nil {
				return pyStringPtr(v)
			}
		}
	}

	// Try to extract user_id / id attribute from context objects.
	rv := reflect.ValueOf(contextObj)
	for rv.Kind() == reflect.Ptr || rv.Kind() == reflect.Interface {
		if rv.IsNil() {
			return nil
		}
		rv = rv.Elem()
	}
	if rv.Kind() == reflect.Struct {
		for _, name := range []string{"UserID", "ID"} {
			field := rv.FieldByName(name)
			if field.IsValid() && field.CanInterface() {
				return pyStringPtr(field.Interface())
			}
		}
	}

	return nil
}

// pyStringPtr mirrors `user_id if isinstance(user_id, str) else str(user_id)`.
func pyStringPtr(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}
