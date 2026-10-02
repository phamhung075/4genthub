package types

// Shared helpers for the API DTO modules. Python counterpart: none (helpers are
// inlined in the pydantic models); kept in one file so entities/summaries/
// responses/bulk/converters can share insertion-ordered dumping and the
// getattr/dict duck typing the converters rely on.

import (
	"fmt"
	"reflect"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// modelDumper is pydantic's BaseModel.model_dump() for the Go DTOs.
type modelDumper interface {
	ModelDump() *entities.OrderedMap[any]
}

// dtoMap builds an insertion-ordered dict from alternating key/value pairs.
func dtoMap(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// dtoOpt dereferences an optional string (nil stays Python None).
func dtoOpt(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

func dtoBool(b *bool) any {
	if b == nil {
		return nil
	}
	return *b
}

func dtoInt(i *int) any {
	if i == nil {
		return nil
	}
	return *i
}

func dtoFloat(f *float64) any {
	if f == nil {
		return nil
	}
	return *f
}

// dtoStrList returns nil for a nil slice (Python None) and the slice otherwise.
func dtoStrList(s []string) any {
	if s == nil {
		return nil
	}
	return s
}

// dtoModelOrNil dumps a nested model, preserving Python None for a nil pointer.
func dtoModelOrNil(v modelDumper) any {
	if v == nil {
		return nil
	}
	rv := reflect.ValueOf(v)
	if rv.Kind() == reflect.Ptr && rv.IsNil() {
		return nil
	}
	return v.ModelDump()
}

// dtoModelList dumps a list of nested models (nil slice = Python None).
func dtoModelList[T modelDumper](xs []T) any {
	if xs == nil {
		return nil
	}
	out := make([]any, len(xs))
	for i, x := range xs {
		out[i] = dtoModelOrNil(x)
	}
	return out
}

// pyStrOf mirrors Python str(x) for the values the converters see: None,
// strings, bools, numbers, and value objects that define __str__ (Go String()).
func pyStrOf(v any) string {
	if v == nil {
		return "None"
	}
	rv := reflect.ValueOf(v)
	for rv.Kind() == reflect.Ptr || rv.Kind() == reflect.Interface {
		if rv.IsNil() {
			return "None"
		}
		rv = rv.Elem()
	}
	if rv.CanInterface() {
		if s, ok := rv.Interface().(fmt.Stringer); ok {
			return s.String()
		}
	}
	return value_objects.PyStr(v)
}

// snakeToCamel maps a Python attribute name to the Go exported name, e.g.
// git_branch_id -> GitBranchId (matched case-insensitively against GitBranchID).
func snakeToCamel(key string) string {
	parts := strings.Split(key, "_")
	for i, p := range parts {
		if p == "" {
			continue
		}
		parts[i] = strings.ToUpper(p[:1]) + p[1:]
	}
	return strings.Join(parts, "")
}

// pyGetattr mirrors getattr(obj, key, default): struct fields (including
// promoted embedded ones) then zero-argument methods. Non-struct values return
// the default, like an object without that attribute.
func pyGetattr(obj any, key string, def any) any {
	if obj == nil {
		return def
	}
	if a, ok := obj.(AttrObject); ok {
		if v, found := pyDictGet(a.Dict, key); found {
			return v
		}
		return def
	}
	want := snakeToCamel(key)
	if mv := reflect.ValueOf(obj).MethodByName(want); mv.IsValid() {
		mt := mv.Type()
		if mt.NumIn() == 0 && mt.NumOut() >= 1 {
			return mv.Call(nil)[0].Interface()
		}
	}
	rv := reflect.ValueOf(obj)
	for rv.Kind() == reflect.Ptr || rv.Kind() == reflect.Interface {
		if rv.IsNil() {
			return def
		}
		rv = rv.Elem()
	}
	if rv.Kind() == reflect.Struct {
		if f := rv.FieldByNameFunc(func(n string) bool { return strings.EqualFold(n, want) }); f.IsValid() && f.CanInterface() {
			return f.Interface()
		}
	}
	return def
}

// AttrObject is a dict exposed as an attribute-style object (Python's
// `class SubtaskObj: setattr(self, key, value)`): converters take their entity branch and
// missing keys fall back to getattr defaults instead of raising KeyError.
type AttrObject struct{ Dict any }

// isPyDict reports whether v is a Python dict for the converters: an
// insertion-ordered map (performance mode) or a plain Go map.
func isPyDict(v any) bool {
	switch v.(type) {
	case *entities.OrderedMap[any], map[string]any:
		return true
	}
	return false
}

// pyDictGet is dict.get(key) returning (value, found).
func pyDictGet(d any, key string) (any, bool) {
	switch m := d.(type) {
	case *entities.OrderedMap[any]:
		v, ok := m.Get(key)
		return v, ok
	case map[string]any:
		v, ok := m[key]
		return v, ok
	}
	return nil, false
}

// pyDictGetDefault is dict.get(key, default) (present-but-None stays None).
func pyDictGetDefault(d any, key string, def any) any {
	if v, ok := pyDictGet(d, key); ok {
		return v
	}
	return def
}

// pyAnySlice iterates a Python list value generically (nil for non-lists).
func pyAnySlice(v any) []any {
	rv := reflect.ValueOf(v)
	for rv.Kind() == reflect.Ptr || rv.Kind() == reflect.Interface {
		if rv.IsNil() {
			return nil
		}
		rv = rv.Elem()
	}
	if rv.Kind() != reflect.Slice && rv.Kind() != reflect.Array {
		return nil
	}
	out := make([]any, rv.Len())
	for i := 0; i < rv.Len(); i++ {
		out[i] = rv.Index(i).Interface()
	}
	return out
}

// pyStringSlice maps a Python iterable of values through str(). A nil or
// non-sequence value yields nil.
func pyStringSlice(v any) []string {
	items := pyAnySlice(v)
	if items == nil {
		return nil
	}
	out := make([]string, len(items))
	for i, it := range items {
		out[i] = pyStrOf(it)
	}
	return out
}

// listOrEmpty mirrors Python `x or []`: a falsy value becomes a fresh empty list.
func listOrEmpty(v any) []string {
	out := pyStringSlice(v)
	if len(out) == 0 {
		return []string{}
	}
	return out
}

// formatDatetime mirrors _format_datetime: None, str passthrough, datetime
// isoformat, anything else None.
func formatDatetime(v any) any {
	if v == nil {
		return nil
	}
	switch x := v.(type) {
	case string:
		return x
	case *string:
		if x == nil {
			return nil
		}
		return *x
	case time.Time:
		return value_objects.IsoFormat(x)
	case *time.Time:
		if x == nil {
			return nil
		}
		return value_objects.IsoFormat(*x)
	}
	return nil
}

// optStrAny builds a `str | None` pointer; a present string stays exact.
func optStrAny(v any) *string {
	if v == nil {
		return nil
	}
	s := pyStrOf(v)
	return &s
}

// optIntAny builds an `int | None` pointer from JSON-like numbers.
func optIntAny(v any) *int {
	if v == nil {
		return nil
	}
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return nil
	}
	i := int(f)
	return &i
}

// asInt is an int field read with a default for a missing/None value.
func asInt(v any, def int) int {
	if f, ok := value_objects.PyFloat(v); ok {
		return int(f)
	}
	return def
}
