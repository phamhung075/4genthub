// Package value_objects ports task_management/domain/value_objects.
package value_objects

import (
	"crypto/rand"
	"fmt"
	"strings"
)

// ValueError mirrors Python's ValueError raised by value-object validation.
type ValueError struct{ Msg string }

func (e *ValueError) Error() string { return e.Msg }

// TypeError mirrors Python's TypeError raised by value-object validation.
type TypeError struct{ Msg string }

func (e *TypeError) Error() string { return e.Msg }

func valueErrorf(format string, a ...any) error { return &ValueError{fmt.Sprintf(format, a...)} }
func typeErrorf(format string, a ...any) error  { return &TypeError{fmt.Sprintf(format, a...)} }

// parseUUID is uuid.UUID(str) returning the canonical form (see PyParseUUID).
func parseUUID(s string) (string, bool) { return PyParseUUID(s) }

// NewUUIDv4 mirrors str(uuid.uuid4()).
func NewUUIDv4() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		panic(err)
	}
	b[6] = b[6]&0x0f | 0x40
	b[8] = b[8]&0x3f | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// EntityId is the base for all UUID-backed entity IDs. Concrete IDs embed it
// in distinct struct types so ProjectId != AgentId at compile time.
type EntityId struct {
	Value string
}

// newEntityId validates and normalizes value; typeName is used in error text.
func newEntityId(typeName, value string) (EntityId, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return EntityId{}, valueErrorf("%s cannot be empty or whitespace", typeName)
	}
	canonical, ok := parseUUID(trimmed)
	if !ok {
		return EntityId{}, valueErrorf(
			"Invalid %s format: '%s'. Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
			typeName, trimmed)
	}
	return EntityId{Value: canonical}, nil
}

// NewTypedEntityId validates value as an EntityId subclass named typeName (error texts
// embed the class name), for ID types defined outside this package.
func NewTypedEntityId(typeName, value string) (EntityId, error) { return newEntityId(typeName, value) }

func (e EntityId) String() string { return e.Value }

// ToHexFormat returns the ID in hex format (32 chars without dashes).
func (e EntityId) ToHexFormat() string { return strings.ReplaceAll(e.Value, "-", "") }

// ToCanonicalFormat returns the ID in canonical UUID format (with dashes).
func (e EntityId) ToCanonicalFormat() string { return e.Value }

// ValueErrorf builds a *ValueError (Python ValueError) for use by other domain packages.
func ValueErrorf(format string, a ...any) error { return valueErrorf(format, a...) }

// TypeErrorf builds a *TypeError (Python TypeError) for use by other domain packages.
func TypeErrorf(format string, a ...any) error { return typeErrorf(format, a...) }
