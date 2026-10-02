// Package database ports task_management/infrastructure/database.
package database

import (
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"reflect"
	"strings"

	"agenthub/fastmcp/task_management/domain"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// UserIDNamespace is the namespace UUID for deterministic user ID conversion.
const UserIDNamespace = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

func init() { domain.UserIDNormalizer = NormalizeUserIDToUUID }

// Uuid5 is uuid.uuid5(namespace, name) as a canonical string.
func Uuid5(namespace, name string) string {
	ns, _ := tmvo.PyParseUUID(namespace)
	nsBytes, _ := hex.DecodeString(strings.ReplaceAll(ns, "-", ""))
	h := sha1.New()
	h.Write(nsBytes)
	h.Write([]byte(name))
	sum := h.Sum(nil)[:16]
	sum[6] = sum[6]&0x0f | 0x50
	sum[8] = sum[8]&0x3f | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", sum[0:4], sum[4:6], sum[6:8], sum[8:10], sum[10:16])
}

// GenerateUUIDString returns a new random UUID string.
func GenerateUUIDString() string { return tmvo.NewUUIDv4() }

// NormalizeUserIDToUUID converts any user id string to a valid UUID string: a parseable
// UUID is returned as given (stripped), anything else becomes uuid5(USER_ID_NAMESPACE, id).
func NormalizeUserIDToUUID(userID string) (string, error) {
	if userID == "" {
		return "", &tmvo.ValueError{Msg: "User ID cannot be empty"}
	}
	userID = tmvo.PyStrip(userID)
	if userID == "" {
		return "", &tmvo.ValueError{Msg: "User ID cannot be empty"}
	}
	if _, ok := tmvo.PyParseUUID(userID); ok {
		return userID, nil
	}
	return Uuid5(UserIDNamespace, userID), nil
}

// UUID dialects.
const (
	DialectPostgres = "postgresql"
	DialectSQLite   = "sqlite"
)

// UnifiedUUIDBindParam is UnifiedUUID.process_bind_param: nil stays nil, a value object
// (a struct with a string `Value` field) is unwrapped, a string is stripped and must be a
// UUID or becomes the deterministic uuid5. Go has no UUID object, so PostgreSQL binds the
// canonical string (the driver sends it as uuid) instead of a uuid.UUID.
func UnifiedUUIDBindParam(value any, dialect string) (any, error) {
	if value == nil {
		return nil, nil
	}
	rv := reflect.ValueOf(value)
	if rv.Kind() == reflect.Pointer && rv.IsNil() {
		return nil, nil
	}
	for rv.Kind() == reflect.Pointer {
		rv = rv.Elem()
	}
	if rv.Kind() == reflect.String {
		value = rv.String() // *string and named string types
	}
	if rv.Kind() == reflect.Struct {
		if f := rv.FieldByName("Value"); f.IsValid() && f.Kind() == reflect.String {
			value = f.String()
		}
	}
	s, ok := value.(string)
	if !ok {
		return nil, &tmvo.TypeError{Msg: fmt.Sprintf("Expected UUID, string, or value object with 'value' attribute, got <class '%s'>", pyClassName(value))}
	}
	s = tmvo.PyStrip(s)
	if s == "" {
		return nil, &tmvo.ValueError{Msg: "Empty string is not a valid UUID or user ID"}
	}
	if canonical, ok := tmvo.PyParseUUID(s); ok {
		if dialect == DialectPostgres {
			return canonical, nil
		}
		return s, nil
	}
	return Uuid5(UserIDNamespace, s), nil
}

// UnifiedUUIDResultValue is process_result_value: always the string form.
func UnifiedUUIDResultValue(value any) any {
	if value == nil {
		return nil
	}
	return tmvo.PyStr(value)
}

func pyClassName(v any) string {
	switch v.(type) {
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return "int"
	case float32, float64:
		return "float"
	case bool:
		return "bool"
	case []any, []string:
		return "list"
	case tmvo.OrderedAny, map[string]any:
		return "dict"
	}
	return "object"
}
