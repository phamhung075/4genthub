// Package amtest holds the test helpers shared by the ai_task_planning domain parity
// tests: the Python-generated fixture and the canonical JSON comparison.
package atptest

import (
	"errors"
	"os"
	"path/filepath"
	"regexp"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Fixture loads testdata/atp_cases.json (tests run one directory below the domain package
// root, e.g. domain/entities).
func Fixture(t *testing.T) *entities.OrderedMap[any] {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("..", "testdata", "atp_cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	return v.(*entities.OrderedMap[any])
}

var (
	uuid4Re = regexp.MustCompile(`[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`)
	tsRe    = regexp.MustCompile(`"\d{4}-\d\d-\d\dT[^"]*"`)
	excRe   = regexp.MustCompile(`"exc": "[A-Za-z]+"`)
)

// Canon is the canonical JSON text of a value: Python's json.dumps layout, clock
// timestamps (any ISO datetime outside 1999) replaced by <ts>, random v4 UUIDs by <uuid>,
// and every exception name other than ValueError by Error (Python raises AttributeError /
// TypeError / FileNotFoundError where Go has one error kind).
func Canon(t *testing.T, v any) string {
	t.Helper()
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	s = uuid4Re.ReplaceAllString(s, "<uuid>")
	s = tsRe.ReplaceAllStringFunc(s, func(m string) string {
		if len(m) > 6 && m[1:6] == "1999-" {
			return m
		}
		return `"<ts>"`
	})
	return excRe.ReplaceAllStringFunc(s, func(m string) string {
		if m == `"exc": "ValueError"` {
			return m
		}
		return `"exc": "Error"`
	})
}

// ErrMap is Python's `{"exc": type, "msg": str}` result shape for an error (msg only for
// ValueError).
func ErrMap(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	var ve *tmvo.ValueError
	if errors.As(err, &ve) {
		m.Set("exc", "ValueError")
		m.Set("msg", ve.Msg)
	} else {
		m.Set("exc", "Error")
		m.Set("msg", "")
	}
	return m
}

// Result wraps a value or error in the fixture's {"ok": v} / {"exc": ...} shape.
func Result(v any, err error) *entities.OrderedMap[any] {
	if err != nil {
		return ErrMap(err)
	}
	m := entities.NewOrderedMap[any]()
	m.Set("ok", v)
	return m
}

// Obj builds an ordered object from alternating key / value arguments.
func Obj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// Items returns the entries of a fixture array.
func Items(v any) []any { return v.([]any) }

// Map returns a fixture object.
func Map(v any) *entities.OrderedMap[any] { return v.(*entities.OrderedMap[any]) }

// Field returns an object member.
func Field(v any, key string) any {
	x, _ := Map(v).Get(key)
	return x
}

// Str returns a fixture string member ("" when null).
func Str(v any, key string) string {
	s, _ := Field(v, key).(string)
	return s
}

// Strs returns a fixture array of strings (nil for null).
func Strs(v any) []string {
	items, ok := v.([]any)
	if !ok {
		return nil
	}
	out := make([]string, len(items))
	for i, x := range items {
		out[i] = x.(string)
	}
	return out
}
